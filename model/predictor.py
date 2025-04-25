def predict_trend(symbol, ohlcv):
    closes = [c[4] for c in ohlcv]
    if closes[-1] > closes[-2] > closes[-3]:
        return "LONG"
    elif closes[-1] < closes[-2] < closes[-3]:
        return "SHORT"
    return "NEUTRAL"
