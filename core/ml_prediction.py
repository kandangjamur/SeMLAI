import os
import pandas as pd
import numpy as np
import logging
import joblib
from datetime import datetime
import traceback
from core.candle_patterns import (
    is_bullish_engulfing, is_bearish_engulfing, is_doji,
    is_hammer, is_shooting_star, is_three_white_soldiers,
    is_three_black_crows
)

# Get logger
logger = logging.getLogger("crypto-signal-bot")


class MLPredictor:
    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.model_path = os.path.join('models', 'random_forest_model.joblib')

        # Track expected feature names
        self.expected_features = None

        # Default features for prediction
        self.default_features = [
            'rsi', 'macd', 'macd_signal', 'bb_upper', 'bb_lower',
            'atr', 'volume', 'volume_sma_20', 'bullish_engulfing',
            'bearish_engulfing', 'doji', 'hammer', 'shooting_star',
            'three_white_soldiers', 'three_black_crows'
        ]

        self.load_model()

    def load_model(self):
        """Load the trained ML model if available"""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                self.model_loaded = True

                # Try to get feature names the model was trained on
                if hasattr(self.model, 'feature_names_in_'):
                    self.expected_features = list(self.model.feature_names_in_)
                    logger.info(
                        f"ML model loaded with {len(self.expected_features)} expected features")
                else:
                    logger.warning(
                        "ML model doesn't expose expected feature names")

                logger.info(f"ML model loaded from {self.model_path}")
            else:
                logger.warning(
                    f"ML model not found at {self.model_path}. Using heuristic prediction.")
        except Exception as e:
            logger.error(f"Error loading ML model: {str(e)}")
            self.model_loaded = False

    def prepare_features(self, df):
        """Prepare features for ML prediction including candlestick patterns"""
        try:
            if df.empty or len(df) < 20:
                return None

            # Get latest data
            latest_index = df.index[-1]

            # Check for required technical indicators
            required = ['rsi', 'macd', 'macdsignal',
                        'upper_band', 'lower_band', 'atr', 'volume']
            if not all(ind in df.columns for ind in required):
                missing = [ind for ind in required if ind not in df.columns]
                logger.warning(
                    f"Missing required indicators for ML prediction: {missing}")
                return None

            # Calculate volume SMA if not in dataframe
            if 'volume_sma20' not in df.columns:
                df['volume_sma20'] = df['volume'].rolling(window=20).mean()

            # Calculate candlestick patterns
            try:
                bullish_engulfing_pattern = float(
                    is_bullish_engulfing(df).iloc[-1])
                bearish_engulfing_pattern = float(
                    is_bearish_engulfing(df).iloc[-1])
                doji_pattern = float(is_doji(df).iloc[-1])
                hammer_pattern = float(is_hammer(df).iloc[-1])
                shooting_star_pattern = float(is_shooting_star(df).iloc[-1])
                three_white_soldiers_pattern = float(
                    is_three_white_soldiers(df).iloc[-1])
                three_black_crows_pattern = float(
                    is_three_black_crows(df).iloc[-1])
            except Exception as pattern_error:
                logger.error(
                    f"Error calculating candlestick patterns: {str(pattern_error)}")
                bullish_engulfing_pattern = bearish_engulfing_pattern = doji_pattern = 0
                hammer_pattern = shooting_star_pattern = three_white_soldiers_pattern = three_black_crows_pattern = 0

            # Basic features always available
            features = {
                'rsi': df['rsi'].iloc[-1],
                'macd': df['macd'].iloc[-1],
                'macd_signal': df['macdsignal'].iloc[-1],
                'bb_upper': df['upper_band'].iloc[-1],
                'bb_lower': df['lower_band'].iloc[-1],
                'atr': df['atr'].iloc[-1],
                'volume': df['volume'].iloc[-1],
                'volume_sma_20': df['volume_sma20'].iloc[-1],
                'bullish_engulfing': bullish_engulfing_pattern,
                'bearish_engulfing': bearish_engulfing_pattern,
                'doji': doji_pattern,
                'hammer': hammer_pattern,
                'shooting_star': shooting_star_pattern,
                'three_white_soldiers': three_white_soldiers_pattern,
                'three_black_crows': three_black_crows_pattern
            }

            return features

        except Exception as e:
            logger.error(f"Error preparing ML features: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    def predict(self, symbol, df):
        """
        Predict trade direction and confidence using ML or heuristics

        Args:
            symbol (str): Trading pair symbol
            df (pd.DataFrame): DataFrame with OHLCV and indicators data

        Returns:
            dict: Prediction result including direction and confidence
        """
        try:
            # Prepare features
            features = self.prepare_features(df)
            if not features:
                logger.warning(
                    f"[{symbol}] Could not prepare features for ML prediction")
                return self.heuristic_prediction(df)

            # Use ML model if available
            if self.model_loaded:
                try:
                    # Handle feature alignment with model expectations
                    if self.expected_features:
                        # Model has defined expected features
                        X_dict = {}
                        for feature in self.expected_features:
                            if feature in features:
                                X_dict[feature] = features[feature]
                            else:
                                # Use a default value for missing features
                                logger.debug(
                                    f"[{symbol}] Using default value for missing feature: {feature}")
                                X_dict[feature] = 0.0

                        # Create DataFrame with aligned features
                        X = pd.DataFrame(
                            [X_dict], columns=self.expected_features)
                    else:
                        # No expected features, use all available
                        feature_names = list(features.keys())
                        X = pd.DataFrame(
                            [list(features.values())], columns=feature_names)

                    # Log the feature data used for prediction
                    logger.debug(f"[{symbol}] Features prepared: {features}")

                    # Make prediction
                    prediction = self.model.predict(X)[0]
                    proba = self.model.predict_proba(X)[0]
                    confidence = float(proba[prediction] * 100)

                    direction = "LONG" if prediction == 1 else "SHORT"
                    logger.info(
                        f"[{symbol}] ML prediction: {direction} with {confidence:.2f}% confidence")

                    # Cap confidence at 98%
                    confidence = min(confidence, 98.0)

                    # Log influential features
                    self._log_important_features(symbol, features, direction)

                    return {
                        'direction': direction,
                        'confidence': confidence,
                        'source': 'ml_model',
                        'patterns': self._get_active_patterns(features)
                    }
                except Exception as model_error:
                    logger.error(
                        f"[{symbol}] Error in ML prediction: {str(model_error)}")
                    logger.error(traceback.format_exc())
                    return self.heuristic_prediction(df)
            else:
                # Fallback to heuristic prediction
                return self.heuristic_prediction(df)

        except Exception as e:
            logger.error(f"[{symbol}] Error in ML prediction: {str(e)}")
            return {
                'direction': None,
                'confidence': 0,
                'source': 'error'
            }

    def _log_important_features(self, symbol, features, direction):
        """Log the most influential features for this prediction"""
        if direction == "LONG":
            # Log bullish patterns
            if features.get('bullish_engulfing', 0) > 0:
                logger.info(f"[{symbol}] Bullish Engulfing pattern detected")
            if features.get('hammer', 0) > 0:
                logger.info(f"[{symbol}] Hammer pattern detected")
            if features.get('three_white_soldiers', 0) > 0:
                logger.info(
                    f"[{symbol}] Three White Soldiers pattern detected")
        else:
            # Log bearish patterns
            if features.get('bearish_engulfing', 0) > 0:
                logger.info(f"[{symbol}] Bearish Engulfing pattern detected")
            if features.get('shooting_star', 0) > 0:
                logger.info(f"[{symbol}] Shooting Star pattern detected")
            if features.get('three_black_crows', 0) > 0:
                logger.info(f"[{symbol}] Three Black Crows pattern detected")

        # Log doji for both
        if features.get('doji', 0) > 0:
            logger.info(f"[{symbol}] Doji pattern detected")

    def _get_active_patterns(self, features):
        """Get list of active candlestick patterns from features"""
        active_patterns = []

        if features.get('bullish_engulfing', 0) > 0:
            active_patterns.append('Bullish Engulfing')
        if features.get('bearish_engulfing', 0) > 0:
            active_patterns.append('Bearish Engulfing')
        if features.get('doji', 0) > 0:
            active_patterns.append('Doji')
        if features.get('hammer', 0) > 0:
            active_patterns.append('Hammer')
        if features.get('shooting_star', 0) > 0:
            active_patterns.append('Shooting Star')
        if features.get('three_white_soldiers', 0) > 0:
            active_patterns.append('Three White Soldiers')
        if features.get('three_black_crows', 0) > 0:
            active_patterns.append('Three Black Crows')

        return active_patterns

    def heuristic_prediction(self, df):
        """Fallback heuristic-based prediction including candlestick patterns"""
        try:
            if df.empty or len(df) < 20:
                return {'direction': None, 'confidence': 0, 'source': 'heuristic'}

            latest = df.iloc[-1]

            # Check for required indicators
            if 'rsi' not in df.columns or 'macd' not in df.columns or 'macdsignal' not in df.columns:
                logger.warning(
                    "Missing basic indicators for heuristic prediction")
                return {'direction': None, 'confidence': 0, 'source': 'heuristic'}

            # Calculate candlestick patterns
            try:
                bullish_engulfing = is_bullish_engulfing(df).iloc[-1]
                bearish_engulfing = is_bearish_engulfing(df).iloc[-1]
                doji = is_doji(df).iloc[-1]
                hammer = is_hammer(df).iloc[-1]
                shooting_star = is_shooting_star(df).iloc[-1]
                three_white_soldiers = is_three_white_soldiers(df).iloc[-1]
                three_black_crows = is_three_black_crows(df).iloc[-1]
            except Exception:
                bullish_engulfing = bearish_engulfing = doji = hammer = False
                shooting_star = three_white_soldiers = three_black_crows = False

            # Simple heuristic logic
            rsi = latest['rsi']
            macd = latest['macd']
            macd_signal = latest['macdsignal']

            # Calculate scores for long and short
            long_score = 0
            short_score = 0
            active_patterns = []

            # RSI logic
            if rsi < 30:  # Oversold
                long_score += 20
            elif rsi > 70:  # Overbought
                short_score += 20

            # MACD logic
            if macd > macd_signal:
                long_score += 15
            else:
                short_score += 15

            # Bollinger Bands logic if available
            if 'upper_band' in df.columns and 'lower_band' in df.columns:
                price = latest['close']
                upper = latest['upper_band']
                lower = latest['lower_band']

                if price < lower * 1.01:  # Near lower band
                    long_score += 15
                elif price > upper * 0.99:  # Near upper band
                    short_score += 15

            # Candlestick pattern logic (higher weight than technical indicators)
            if bullish_engulfing:
                long_score += 25
                active_patterns.append('Bullish Engulfing')
            if bearish_engulfing:
                short_score += 25
                active_patterns.append('Bearish Engulfing')
            if hammer:
                long_score += 20
                active_patterns.append('Hammer')
            if shooting_star:
                short_score += 20
                active_patterns.append('Shooting Star')
            if three_white_soldiers:
                long_score += 30
                active_patterns.append('Three White Soldiers')
            if three_black_crows:
                short_score += 30
                active_patterns.append('Three Black Crows')
            if doji:
                # Doji is indecision, slightly favor the non-dominant direction as potential reversal
                if long_score > short_score:
                    short_score += 10
                else:
                    long_score += 10
                active_patterns.append('Doji')

            # Determine direction and confidence
            if long_score > short_score:
                direction = "LONG"
                # Base 50% + up to 48% (cap at 98%)
                confidence = 50 + min(long_score, 48)
            else:
                direction = "SHORT"
                # Base 50% + up to 48% (cap at 98%)
                confidence = 50 + min(short_score, 48)

            logger.info(
                f"Heuristic prediction: {direction} with {confidence:.2f}% confidence")
            if active_patterns:
                logger.info(f"Active patterns: {', '.join(active_patterns)}")

            return {
                'direction': direction,
                'confidence': confidence,
                'source': 'heuristic',
                'patterns': active_patterns
            }

        except Exception as e:
            logger.error(f"Error in heuristic prediction: {str(e)}")
            return {
                'direction': None,
                'confidence': 0,
                'source': 'error'
            }


# Create global instance
ml_predictor = MLPredictor()

# Convenience function


def get_ml_prediction(symbol, df):
    """Get ML prediction for the given symbol and data"""
    return ml_predictor.predict(symbol, df)
