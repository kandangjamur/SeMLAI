import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from joblib import load
from utils.logger import log
from core.candle_patterns import is_bullish_engulfing, is_bearish_engulfing, is_doji, is_hammer, is_shooting_star, is_three_white_soldiers, is_three_black_crows
from core.indicators import calculate_indicators

def load_model(model_path="models/rf_model.joblib"):
    try:
        model = load(model_path)
        log("Random Forest model loaded successfully")
        return model
    except Exception as e:
        log(f"Error loading model: {e}", level='ERROR')
        return None

def prepare_features(df):
    try:
        if len(df) < 50 or df['close'].std() <= 0:
            log("Insufficient data for feature preparation", level='WARNING')
            return None

        df = df.copy()
        # اصل انڈیکیٹرز استعمال کرو
        df = calculate_indicators(df)
        
        # اضافی فیچرز
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

        features = [
            "rsi", "macd", "macd_signal", "bb_upper", "bb_lower", "atr",
            "volume", "volume_sma_20", "bullish_engulfing", "bearish_engulfing",
            "doji", "hammer", "shooting_star", "three_white_soldiers", "three_black_crows"
        ]
        
        # NaN ویلیوز کو ہینڈل کرو
        df[features] = df[features].fillna({
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
        
        X = df[features].iloc[-1].values.reshape(1, -1)
        if np.any(np.isnan(X)):
            log("NaN values in features after filling", level='WARNING')
            return None
        return X
    except Exception as e:
        log(f"Error preparing features: {e}", level='ERROR')
        return None

def predict_confidence(symbol, df, model_path="models/rf_model.joblib"):
    try:
        model = load_model(model_path)
        if model is None:
            return 0.0

        X = prepare_features(df)
        if X is None:
            return 0.0

        confidence = model.predict_proba(X)[0][1] * 100  # فیصد میں واپس کرو
        confidence = min(95, round(confidence, 2))
        log(f"[{symbol}] ML Confidence: {confidence}%")
        return confidence
    except Exception as e:
        log(f"[{symbol}] Error in predict_confidence: {e}", level='ERROR')
        return 0.0
