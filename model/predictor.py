import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from joblib import load
from utils.logger import log
from core.candle_patterns import is_bullish_engulfing, is_bearish_engulfing, is_doji, is_hammer, is_shooting_star, is_three_white_soldiers, is_three_black_crows
from core.indicators import calculate_indicators
from data.backtest import get_tp1_hit_rate

class Predictor:
    def __init__(self):
        self.model = None
        self.model_path = "models/rf_model.joblib"
        self.features = [
            "rsi", "macd", "macd_signal", "bb_upper", "bb_lower", "atr",
            "volume", "volume_sma_20", "bullish_engulfing", "bearish_engulfing",
            "doji", "hammer", "shooting_star", "three_white_soldiers", "three_black_crows"
        ]
        self.last_signals = {}  # To track last signal per symbol and timeframe
        self.min_confidence_threshold = 0.75  # 75% minimum confidence

    def load_model(self):
        """Load the Random Forest model."""
        try:
            self.model = load(self.model_path)
            log("Random Forest model loaded successfully")
            return self.model
        except Exception as e:
            log(f"Error loading model: {e}", level='ERROR')
            return None

    async def calculate_take_profits(self, df, signal):
        """Calculate TP1, TP2, TP3 based on recent volatility."""
        try:
            volatility = df['close'].pct_change().std() * np.sqrt(252)
            current_price = df['close'].iloc[-1]
            
            if signal == 'LONG':
                tp1 = current_price * (1 + 0.5 * volatility)
                tp2 = current_price * (1 + 1.0 * volatility)
                tp3 = current_price * (1 + 1.5 * volatility)
            else:  # SHORT
                tp1 = current_price * (1 - 0.5 * volatility)
                tp2 = current_price * (1 - 1.0 * volatility)
                tp3 = current_price * (1 - 1.5 * volatility)
            
            # Ensure TP values are valid
            if any(np.isclose([tp1, tp2, tp3], current_price, rtol=1e-5)) or any(v <= 0 for v in [tp1, tp2, tp3]):
                log("Invalid TP values calculated, using fallback.", level='WARNING')
                return None, None, None
            
            return tp1, tp2, tp3
        except Exception as e:
            log(f"Error calculating take profits: {e}", level='ERROR')
            return None, None, None

    def prepare_features(self, df, symbol, timeframe):
        """Prepare features for prediction."""
        try:
            if len(df) < 50 or df['close'].std() <= 0:
                log(f"[{symbol}] Insufficient data for feature preparation", level='WARNING')
                return None

            df = df.copy()
            # Calculate indicators
            df = calculate_indicators(df)
            if df is None or len(df) < 50:
                log(f"[{symbol}] Failed to calculate indicators", level='WARNING')
                return None
            
            # Additional features
            df["bb_upper"] = df["close"] * 1.02
            df["bb_lower"] = df["close"] * 0.98
            df["atr"] = (df["high"] - df["low"]).rolling(window=14).mean()
            df["volume_sma_20"] = df["volume"].rolling(window=20).mean()
            df["bullish_engulfing"] = df.apply(lambda x: is_bullish_engulfing(df.loc[:x.name]), axis=1).astype(int)
            df["bearish_engulfing"] = df.apply(lambda x: is_bearish_engulfing(df.loc[:x.name]), axis=1).astype(int)
            df["doji"] = df.apply(lambda x: is_doji(df.loc[:x.name]), axis=1).astype(int)
            df["hammer"] = df.apply(lambda x: is_hammer(df.loc[:x.name]), axis=1).astype(int)
            df["shooting_star"] = df.apply(lambda x: is_shooting_star(df.loc[:x.name]), axis=1).astype(int)
            df["three_white_soldiers"] = df.apply(lambda x: is_three_white_soldiers(df.loc[:x.name]), axis=1).astype(int)
            df["three_black_crows"] = df.apply(lambda x: is_three_black_crows(df.loc[:x.name]), axis=1).astype(int)

            # Handle NaN values
            df[self.features] = df[self.features].fillna({
                "rsi": 50.0,
                "macd": 0.0,
                "macd_signal": 0.0,
                "atr": df["atr"].mean() if not df["atr"].isna().all() else 0.0,
                "volume_sma_20": df["volume"].mean() if not df["volume"].isna().all() else 0.0,
                "bb_upper": df["close"] * 1.02,
                "bb_lower": df["close"] * 0.98,
                "bullish_engulfing": 0,
                "bearish_engulfing": 0,
                "doji": 0,
                "hammer": 0,
                "shooting_star": 0,
                "three_white_soldiers": 0,
                "three_black_crows": 0,
                "volume": df["volume"].mean() if not df["volume"].isna().all() else 0.0
            })
            
            # Select features for prediction
            X = df[self.features].iloc[-1:]
            if X.isna().any().any():
                log(f"[{symbol}] NaN values in features after filling", level='WARNING')
                return None
            return X
        except Exception as e:
            log(f"[{symbol}] Error preparing features: {e}", level='ERROR')
            return None

    async def predict_signal(self, symbol, df, timeframe):
        """Generate trading signal with confidence and TP probabilities."""
        try:
            if self.model is None:
                self.model = self.load_model()
                if self.model is None:
                    return None, 0, (0.7, 0.5, 0.3)

            # Prepare features
            X = self.prepare_features(df, symbol, timeframe)
            if X is None:
                return None, 0, (0.7, 0.5, 0.3)

            # Predict signal
            prediction = self.model.predict(X)[0]
            confidence = self.model.predict_proba(X)[0].max()
            
            # Normalize confidence
            confidence = min(max(confidence, 0), 0.95) * 100  # Cap at 95%
            
            # Apply threshold
            if confidence < self.min_confidence_threshold * 100:
                log(f"[{symbol}] Confidence {confidence:.2f}% below threshold {self.min_confidence_threshold*100}%")
                return None, 0, (0.7, 0.5, 0.3)
            
            signal = 'LONG' if prediction == 1 else 'SHORT'
            
            # Check for repeated signals
            key = f"{symbol}_{timeframe}"
            if key in self.last_signals:
                last_signal, last_time = self.last_signals[key]
                if last_signal == signal and (pd.Timestamp.now() - last_time).seconds < 3600:
                    log(f"[{symbol}] Skipping repeated signal for {key}")
                    return None, 0, (0.7, 0.5, 0.3)
            
            # Update last signal
            self.last_signals[key] = (signal, pd.Timestamp.now())
            
            # Calculate TP probabilities
            tp1_prob = get_tp1_hit_rate(symbol, timeframe)
            tp2_prob = tp1_prob * 0.8  # Assume TP2 is 80% of TP1 probability
            tp3_prob = tp1_prob * 0.6  # Assume TP3 is 60% of TP1 probability
            
            # Calculate TP values
            tp1, tp2, tp3 = await self.calculate_take_profits(df, signal)
            if not all([tp1, tp2, tp3]):
                log(f"[{symbol}] Invalid TP values, skipping signal")
                return None, 0, (0.7, 0.5, 0.3)
            
            log(f"[{symbol}] Signal for {timeframe}: {signal}, Confidence: {confidence:.2f}%, TP1: {tp1_prob:.2f}%")
            return {
                'direction': signal,
                'confidence': confidence,
                'tp1': tp1,
                'tp2': tp2,
                'tp3': tp3,
                'tp1_possibility': tp1_prob,
                'tp2_possibility': tp2_prob,
                'tp3_possibility': tp3_prob,
                'timeframe': timeframe
            }
        except Exception as e:
            log(f"[{symbol}] Error in predict_signal: {e}", level='ERROR')
            return None, 0, (0.7, 0.5, 0.3)
