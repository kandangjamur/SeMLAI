import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
import os
from core.candle_patterns import (
    is_bullish_engulfing, is_bearish_engulfing, is_doji, is_hammer, is_shooting_star,
    is_three_white_soldiers, is_three_black_crows
)
from data.backtest import get_tp_hit_rates
from utils.logger import log

class SignalPredictor:
    def __init__(self, model_path="models/rf_model.joblib"):
        self.model = None
        self.features = [
            "rsi", "macd", "macd_signal", "bb_upper", "bb_lower", "atr", "volume",
            "volume_sma_20", "bullish_engulfing", "bearish_engulfing", "doji",
            "hammer", "shooting_star", "three_white_soldiers", "three_black_crows"
        ]
        self.min_confidence_threshold = 0.70  # Adjusted to match main.py
        self.last_signals = {}  # Store last signal timestamp per symbol and timeframe
        
        try:
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
                log("Random Forest model loaded successfully")
            else:
                log(f"Model file not found at {model_path}", level="ERROR")
                raise FileNotFoundError(f"Model file {model_path} not found")
        except Exception as e:
            log(f"Error loading model: {str(e)}", level="ERROR")
            raise

    def prepare_features(self, df: pd.DataFrame):
        try:
            feature_df = pd.DataFrame(index=df.index)
            
            # Technical indicators
            for feature in ["rsi", "macd", "macd_signal", "bb_upper", "bb_lower", "atr", "volume"]:
                if feature in df.columns:
                    feature_df[feature] = df[feature]
                else:
                    log(f"Feature {feature} not found in DataFrame", level="WARNING")
                    feature_df[feature] = 0.0
            
            # Volume SMA
            feature_df["volume_sma_20"] = df["volume"].rolling(window=20).mean().fillna(0.0)
            
            # Candlestick patterns
            feature_df["bullish_engulfing"] = is_bullish_engulfing(df).astype(float)
            feature_df["bearish_engulfing"] = is_bearish_engulfing(df).astype(float)
            feature_df["doji"] = is_doji(df).astype(float)
            feature_df["hammer"] = is_hammer(df).astype(float)
            feature_df["shooting_star"] = is_shooting_star(df).astype(float)
            feature_df["three_white_soldiers"] = is_three_white_soldiers(df).astype(float)
            feature_df["three_black_crows"] = is_three_black_crows(df).astype(float)
            
            # Ensure all expected features are present
            for feature in self.features:
                if feature not in feature_df.columns:
                    log(f"Adding missing feature {feature} with zeros", level="WARNING")
                    feature_df[feature] = 0.0
            
            # Reorder columns to match self.features
            feature_df = feature_df[self.features]
            
            # Handle NaN values
            feature_df = feature_df.fillna(0.0)
            
            if feature_df.isna().any().any():
                log("NaN values detected after filling in features", level="WARNING")
                return None
                
            return feature_df
        except Exception as e:
            log(f"Error preparing features: {str(e)}", level="ERROR")
            return None

    async def calculate_take_profits(self, df: pd.DataFrame, direction: str, current_price: float):
        try:
            # Use ATR for more realistic TP/SL
            atr = df["atr"].iloc[-1]
            
            if direction == "LONG":
                tp1 = current_price + (0.5 * atr)
                tp2 = current_price + (1.0 * atr)
                tp3 = current_price + (1.5 * atr)
                sl = current_price - (1.5 * atr)
            else:  # SHORT
                tp1 = current_price - (0.5 * atr)
                tp2 = current_price - (1.0 * atr)
                tp3 = current_price - (1.5 * atr)
                sl = current_price + (1.5 * atr)
            
            # Ensure TP/SL are valid
            if not all([tp1, tp2, tp3, sl]) or any(np.isclose([tp1, tp2, tp3, sl], current_price, rtol=1e-5)):
                log("Invalid TP/SL values calculated", level="WARNING")
                return None, None, None, None
            
            return tp1, tp2, tp3, sl
        except Exception as e:
            log(f"Error calculating TP/SL: {str(e)}", level="ERROR")
            return None, None, None, None

    async def predict_signal(self, symbol: str, df: pd.DataFrame, timeframe: str = "15m"):
        try:
            if self.model is None:
                log("Model not loaded", level="ERROR")
                return None
                
            # Check for recent signals to prevent duplicates
            signal_key = f"{symbol}_{timeframe}"
            last_signal_time = self.last_signals.get(signal_key)
            if last_signal_time and (pd.Timestamp.now() - last_signal_time).total_seconds() < 3600:
                log(f"[{symbol}] Skipping duplicate signal within 1 hour", level="INFO")
                return None
                
            # Prepare features
            features = self.prepare_features(df)
            if features is None or len(features) == 0:
                log(f"[{symbol}] No valid features for prediction", level="WARNING")
                return None
                
            # Predict
            current_features = features.iloc[-1:].reindex(columns=self.features)
            prediction_proba = self.model.predict_proba(current_features)[0]
            prediction = self.model.predict(current_features)[0]
            
            # Determine direction and confidence
            direction = "LONG" if prediction == 1 else "SHORT"
            confidence = min(max(prediction_proba.max() * 100, 0), 95)
            
            if confidence < self.min_confidence_threshold * 100:
                log(f"[{symbol}] Low confidence: {confidence:.2f}%", level="INFO")
                return None
                
            # Get current price
            current_price = df["close"].iloc[-1]
            
            # Calculate TP/SL
            tp1, tp2, tp3, sl = await self.calculate_take_profits(df, direction, current_price)
            if any(x is None for x in [tp1, tp2, tp3, sl]):
                log(f"[{symbol}] Invalid TP/SL values", level="WARNING")
                return None
                
            # Get TP hit rates
            tp1_hit_rate, tp2_hit_rate, tp3_hit_rate = await get_tp_hit_rates(symbol, timeframe)
            
            # Create signal
            signal = {
                "symbol": symbol,
                "direction": direction,
                "entry": current_price,
                "tp1": round(tp1, 4),
                "tp2": round(tp2, 4),
                "tp3": round(tp3, 4),
                "sl": round(sl, 4),
                "confidence": confidence,
                "tp1_possibility": tp1_hit_rate,
                "tp2_possibility": tp2_hit_rate,
                "tp3_possibility": tp3_hit_rate,
                "timeframe": timeframe,
                "timestamp": pd.Timestamp.now(tz=ZoneInfo("Asia/Karachi")).isoformat()
            }
            
            # Update last signal time
            self.last_signals[signal_key] = pd.Timestamp.now()
            
            log(f"[{symbol}] Signal generated - Direction: {direction}, Confidence: {confidence:.2f}%")
            return signal
            
        except Exception as e:
            log(f"[{symbol}] Error predicting signal: {str(e)}", level="ERROR")
            return None
