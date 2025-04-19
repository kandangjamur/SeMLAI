def predict_trend(symbol, ohlcv):
    closes = [c[4] for c in ohlcv]
    if len(closes) < 50:
        return "UNKNOWN"

    last_close = closes[-1]
    prev_close = closes[-2]
    trend_strength = last_close - prev_close

    if trend_strength > 0:
        return "LONG"
    elif trend_strength < 0:
        return "SHORT"
    else:
        return "UNKNOWN"
