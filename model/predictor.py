import joblib
import numpy as np
import os

MODEL_PATH = "model/signal_model.pkl"

def load_model():
    """Load the trained ML model from disk."""
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError("Trained model not found. Please train the model first.")
    return joblib.load(MODEL_PATH)

def prepare_features(data: dict) -> np.ndarray:
    """
    Convert raw input indicators into an ML-friendly feature array.
    
    Args:
        data (dict): A dictionary of technical indicators.
    
    Returns:
        np.ndarray: Formatted features array.
    """
    return np.array([
        data.get("rsi", 50),
        data.get("macd", 0),
        data.get("macd_signal", 0),
        data.get("ema_fast", 0),
        data.get("ema_slow", 0),
        data.get("volume", 0),
        data.get("price_change", 0),
        data.get("whale_alert", 0),
        data.get("sentiment_score", 0)
    ]).reshape(1, -1)

def predict_signal(indicator_data: dict) -> dict:
    """
    Predicts signal (buy/sell/hold) using the trained ML model.

    Args:
        indicator_data (dict): Technical + sentiment indicator values.

    Returns:
        dict: Prediction result with label and confidence score.
    """
    try:
        model = load_model()
        features = prepare_features(indicator_data)
        prediction = model.predict(features)[0]
        confidence = np.max(model.predict_proba(features))
        return {
            "signal": prediction,  # e.g., 'buy', 'sell', 'hold'
            "confidence": round(confidence * 100, 2)
        }
    except Exception as e:
        return {
            "signal": "hold",
            "confidence": 0.0,
            "error": str(e)
        }
