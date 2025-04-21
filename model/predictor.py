def predict_trend(symbol, ohlcv):
    closes = [c[4] for c in ohlcv]
    if closes[-1] > closes[-5] and closes[-1] > closes[-10]:
        return "LONG"
    elif closes[-1] < closes[-5] and closes[-1] < closes[-10]:
        return "SHORT"
    else:
        return "RANGE"
