def predict_trend(symbol, ohlcv):
    closes = [c[4] for c in ohlcv]  # Extracting closing prices
    if closes[-1] > closes[-2] > closes[-3]:  # Uptrend
        return "LONG"
    elif closes[-1] < closes[-2] < closes[-3]:  # Downtrend
        return "SHORT"
    else:
        return None  # Don't return "NEUTRAL", now returning None for no signal
