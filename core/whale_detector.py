def whale_check(symbol, exchange):
    try:
        ticker = exchange.fetch_ticker(symbol)
        volume = ticker.get('quoteVolume', 0)
        return volume > 1000000  # 1M+ USDT volume
    except:
        return False
