def predict_trend(symbol, ohlcv):
    closes = [c[4] for c in ohlcv][-5:]
    if closes[-1] > closes[0]:
        return "LONG"
    else:
        return "SHORT"
