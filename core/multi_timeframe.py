import ccxt

def multi_timeframe_boost(symbol, exchange, base_direction):
    """
    Checks if the trend is aligned across 1h and 4h timeframes.
    Returns a boost (e.g., +5) if both timeframes match base_direction (LONG/SHORT).
    """
    boost = 0
    try:
        ohlcv_1h = exchange.fetch_ohlcv(symbol, '1h', limit=100)
        ohlcv_4h = exchange.fetch_ohlcv(symbol, '4h', limit=100)
        dir_1h = "LONG" if ohlcv_1h[-1][4] > ohlcv_1h[-1][1] else "SHORT"
        dir_4h = "LONG" if ohlcv_4h[-1][4] > ohlcv_4h[-1][1] else "SHORT"
        if dir_1h == base_direction and dir_4h == base_direction:
            boost = 5
    except Exception as e:
        boost = 0
    return boost
