# core/engine.py
import ccxt
from core.multi_timeframe import multi_timeframe_boost
from model.predictor import predict_trend
from utils.logger import log

def predict_trend(symbol, exchange):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe="15m", limit=50)
        closes = [c[4] for c in ohlcv]
        if closes[-1] > closes[-2] > closes[-3]:
            return "LONG"
        elif closes[-1] < closes[-2] < closes[-3]:
            return "SHORT"
        else:
            return "NEUTRAL"
    except Exception as e:
        log(f"❌ Prediction error {symbol}: {e}")
        return "NEUTRAL"
