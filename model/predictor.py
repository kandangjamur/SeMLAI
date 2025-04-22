def predict_trend(symbol, ohlcv):
    closes = [c[4] for c in ohlcv]
    # Very basic example — adjust with multi-timeframe logic as needed.
    if closes[-1] > closes[-5] and closes[-1] > closes[-10]:
        return "LONG"
    elif closes[-1] < closes[-5] and closes[-1] < closes[-10]:
        return "SHORT"
    else:
        return "RANGE"
