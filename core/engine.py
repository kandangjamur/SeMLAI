def predict_trend(symbol, exchange):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe="15m", limit=50)
        closes = [x[4] for x in ohlcv]
        if closes[-1] > closes[-2] > closes[-3]:
            return "LONG"
        elif closes[-1] < closes[-2] < closes[-3]:
            return "SHORT"
        return "LONG"  # default if no trend
    except:
        return "LONG"
