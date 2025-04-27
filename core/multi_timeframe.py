import ccxt

def multi_timeframe_boost(symbol, exchange, direction):
    boost = 0
    try:
        tf_list = ["1h", "4h", "1d"]
        for tf in tf_list:
            candles = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
            if not candles:
                continue
            closes = [x[4] for x in candles]
            if direction == "LONG" and closes[-1] > sum(closes[-20:]) / 20:
                boost += 5
            elif direction == "SHORT" and closes[-1] < sum(closes[-20:]) / 20:
                boost += 5
    except Exception:
        pass
    return boost
