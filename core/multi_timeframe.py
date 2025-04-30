import ccxt

async def multi_timeframe_boost(symbol, exchange, direction):
    boost = 0
    try:
        timeframes = ["15m", "1h", "4h", "1d"]
        for tf in timeframes:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe=tf, limit=50)
            if not ohlcv:
                continue
            closes = [c[4] for c in ohlcv]
            avg_close = sum(closes[-20:]) / 20

            if direction == "LONG" and closes[-1] > avg_close:
                boost += 5
            elif direction == "SHORT" and closes[-1] < avg_close:
                boost += 5
    except Exception:
        pass
    return boost
