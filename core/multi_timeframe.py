import ccxt

def fetch_ohlcv_multiple_timeframes(exchange, symbol, timeframes=['15m', '1h', '4h']):
    all_ohlcv = {}
    for tf in timeframes:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
            all_ohlcv[tf] = ohlcv
        except:
            all_ohlcv[tf] = None
    return all_ohlcv
