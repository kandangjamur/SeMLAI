import numpy as np

def predict_trend(symbol, exchange):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe="15m", limit=50)
        closes = [c[4] for c in ohlcv if c]

        if len(closes) < 3:
            return "NEUTRAL"

        if closes[-1] > closes[-2] > closes[-3]:
            return "LONG"
        elif closes[-1] < closes[-2] < closes[-3]:
            return "SHORT"
        else:
            return "NEUTRAL"

    except Exception as e:
        print(f"Trend Prediction Error for {symbol}: {e}")
        return "NEUTRAL"
