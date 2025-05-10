import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
import os
from core.candle_patterns import (
    is_bullish_engulfing, is_bearish_engulfing, is_doji, is_hammer, is_shooting_star,
    is_three_white_soldiers, is_three_black_crows
)
from utils.logger import log
import pytz
import gc

class SignalPredictor:
    def __init__(self, model_path="models/rf_model.joblib"):
        self.model = None
        self.features = [
            "rsi", "macd", "macd_signal", "atr", "volume",
            "bullish_engulfing", "bearish_engulfing", "doji",
            "hammer", "shooting_star", "three_white_soldiers", "three_black_crows"
        ]
        self.min_confidence_threshold = 0.65  # 65% confidence
        self.last_signals = {}
        
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
            if df.empty or len(df) < 2:
                log("Input DataFrame is empty or too small for feature preparation", level="ERROR")
                return None

            feature_df = pd.DataFrame(index=df.index, dtype="float32")
            
            # Ensure technical indicators are pandas.Series
            for feature in ["rsi", "macd", "macd_signal", "atr", "volume"]:
                if feature in df.columns:
                    feature_series = pd.Series(df[feature], index=df.index, dtype="float32")
                    feature_df[feature] = feature_series.fillna(0.0)
                else:
                    log(f"Feature {feature} not found in DataFrame", level="WARNING")
                    feature_df[feature] = 0.0
            
            # Calculate candlestick patterns
            feature_df["bullish_engulfing"] = pd.Series(is_bullish_engulfing(df), index=df.index, dtype="float32").fillna(0.0)
            feature_df["bearish_engulfing"] = pd.Series(is_bearish_engulfing(df), index=df.index, dtype="float32").fillna(0.0)
            feature_df["doji"] = pd.Series(is_doji(df), index=df.index, dtype="float32").fillna(0.0)
            feature_df["hammer"] = pd.Series(is_hammer(df), index=df.index, dtype="float32").fillna(0.0)
            feature_df["shooting_star"] = pd.Series(is_shooting_star(df), index=df.index, dtype="float32").fillna(0.0)
            feature_df["three_white_soldiers"] = pd.Series(is_three_white_soldiers(df), index=df.index, dtype="float32").fillna(0.0)
            feature_df["three_black_crows"] = pd.Series(is_three_black_crows(df), index=df.index, dtype="float32").fillna(0.0)
            
            for feature in self.features:
                if feature not in feature_df.columns:
                    log(f"Adding missing feature {feature} with zeros", level="WARNING")
                    feature_df[feature] = 0.0
            
            feature_df = feature_df[self.features]
            feature_df = feature_df.fillna(0.0)
            
            if feature_df.isna().any().any():
                log("NaN values detected after filling in features", level="WARNING")
                return None
                
            log(f"Features prepared: {feature_df.iloc[-1].to_dict()}")
            return feature_df
        except Exception as e:
            log(f"Error preparing features: {str(e)}", level="ERROR")
            return None
        finally:
            gc.collect()

    async def calculate_take_profits(self, df: pd.DataFrame, direction: str, current_price: float):
        try:
            atr = df["atr"].iloc[-1]
            if pd.isna(atr) or atr <= 0:
                log("Invalid ATR value for TP/SL calculation", level="WARNING")
                return None, None, None, None
            
            if direction == "LONG":
                tp1 = current_price + (0.15 * atr)
                tp2 = current_price + (0.3 * atr)
                tp3 = current_price + (0.45 * atr)
                sl = current_price - (1.2 * atr)
            else:  # SHORT
                tp1 = current_price - (0.15 * atr)
                tp2 = current_price - (0.3 * atr)
                tp3 = current_price - (0.45 * atr)
                sl = current_price + (1.2 * atr)
            
            if not all([tp1, tp2, tp3, sl]) or any(np.isclose([tp1, tp2, tp3, sl], current_price, rtol=1e-5)):
                log("Invalid TP/SL values calculated", level="WARNING")
                return None, None, None, None
            
            return tp1, tp2, tp3, sl
        except Exception as e:
            log(f"Error calculating TP/SL: {str(e)}", level="ERROR")
            return None, None, None, None
        finally:
            gc.collect()

    async def predict_signal(self, symbol: str, df: pd.DataFrame, timeframe: str = "15m"):
        try:
            if self.model is None:
                log("Model not loaded", level="ERROR")
                return None
                
            signal_key = f"{symbol}_{timeframe}"
            last_signal_time = self.last_signals.get(signal_key)
            if last_signal_time and (pd.Timestamp.now() - last_signal_time).total_seconds() < 3600:
                log(f"[{symbol}] Skipping duplicate signal within 1 hour", level="INFO")
                return None
                
            features = self.prepare_features(df)
            if features is None or len(features) == 0:
                log(f"[{symbol}] No valid features for prediction", level="WARNING")
                return None
                
            current_features = features.iloc[-1:].reindex(columns=self.features)
            prediction_proba = self.model.predict_proba(current_features)[0]
            prediction = self.model.predict(current_features)[0]
            
            # Simplified bullish/bearish conditions
            is_bullish = (
                features["bullish_engulfing"].iloc[-1] > 0 or
                features["hammer"].iloc[-1] > 0 or
                features["three_white_soldiers"].iloc[-1] > 0
            ) and (
                not pd.isna(df["rsi"].iloc[-1]) and df["rsi"].iloc[-1] < 45
            ) and (
                not pd.isna(df["macd"].iloc[-1]) and not pd.isna(df["macd_signal"].iloc[-1]) and
                df["macd"].iloc[-1] > df["macd_signal"].iloc[-1]
            )
            
            is_bearish = (
                features["bearish_engulfing"].iloc[-1] > 0 or
                features["shooting_star"].iloc[-1] > 0 or
                features["three_black_crows"].iloc[-1] > 0
            ) and (
                not pd.isna(df["rsi"].iloc[-1]) and df["rsi"].iloc[-1] > 55
            ) and (
                not pd.isna(df["macd"].iloc[-1]) and not pd.isna(df["macd_signal"].iloc[-1]) and
                df["macd"].iloc[-1] < df["macd_signal"].iloc[-1]
            )
            
            direction = "LONG" if prediction == 1 else "SHORT"
            confidence = min(max(prediction_proba.max(), 0), 0.95) * 100
            
            if is_bullish and direction == "LONG":
                confidence = min(confidence + 25, 95)
            elif is_bearish and direction == "SHORT":
                confidence = min(confidence + 25, 95)
            elif (is_bullish and direction == "SHORT") or (is_bearish and direction == "LONG"):
                confidence = max(confidence - 25, 0)
                
            if confidence < self.min_confidence_threshold * 100:
                log(f"[{symbol}] Low confidence: {confidence:.2f}%", level="INFO")
                return None
                
            current_price = df["close"].iloc[-1]
            
            tp1, tp2, tp3, sl = await self.calculate_take_profits(df, direction, current_price)
            if any(x is None for x in [tp1, tp2, tp3, sl]):
                log(f"[{symbol}] Invalid TP/SL values", level="WARNING")
                return None
                
            # Default TP hit rates
            tp1_hit_rate, tp2_hit_rate, tp3_hit_rate = 0.75, 0.50, 0.25
            
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
                "timestamp": pd.Timestamp.now(tz=pytz.timezone("Asia/Karachi")).isoformat()
            }
            
            self.last_signals[signal_key] = pd.Timestamp.now()
            
            log(f"[{symbol}] Signal generated - Direction: {direction}, Confidence: {confidence:.2f}%")
            return signal
            
        except Exception as e:
            log(f"[{symbol}] Error predicting signal: {str(e)}", level="ERROR")
            return None
        finally:
            if 'features' in locals():
                del features
            gc.collect()
