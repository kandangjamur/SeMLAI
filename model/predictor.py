def predict_trend(symbol, ohlcv):
    if not ohlcv or len(ohlcv) < 10:
        return "UNKNOWN"

    close_prices = [c[4] for c in ohlcv]
    last = close_prices[-1]
    prev = close_prices[-2]

    if last > prev:
        return "LONG"
    elif last < prev:
        return "SHORT"
    else:
        return "LONG"  # Assume momentum continues
