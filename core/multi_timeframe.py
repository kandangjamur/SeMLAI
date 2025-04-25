import time

def multi_timeframe_boost(symbol, exchange, direction):
    try:
        tf_list = ["30m", "1h", "4h"]
        boost = 0
        for tf in tf_list:
            ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=50)
            if not ohlcv:
                continue

            closes = [c[4] for c in ohlcv]
            if direction == "LONG" and closes[-1] > closes[-2] > closes[-3]:
                boost += 3
            elif direction == "SHORT" and closes[-1] < closes[-2] < closes[-3]:
                boost += 3

        return boost
    except Exception as e:
        return 0
