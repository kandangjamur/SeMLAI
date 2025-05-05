import ccxt.async_support as ccxt
from utils.logger import log

async def whale_check(symbol, exchange):
    try:
        # Fetch ticker for volume
        ticker = await exchange.fetch_ticker(symbol)
        quote_volume = ticker.get('quoteVolume', 0)
        if quote_volume < 2000000:  # 2M+ USDT
            log(f"[{symbol}] Insufficient quote volume: {quote_volume}", level='WARNING')
            return False

        # Fetch OHLCV for volume spike
        ohlcv = await exchange.fetch_ohlcv(symbol, '15m', limit=10)
        if len(ohlcv) < 10:
            log(f"[{symbol}] Insufficient OHLCV data", level='WARNING')
            return False

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df["volume_sma_5"] = df["volume"].rolling(window=5).mean()
        latest = df.iloc[-1]
        if latest["volume"] < 2 * latest["volume_sma_5"]:
            log(f"[{symbol}] No volume spike detected", level='WARNING')
            return False

        # Fetch order book for depth
        order_book = await exchange.fetch_order_book(symbol, limit=10)
        bid_volume = sum([bid[1] for bid in order_book['bids']])
        ask_volume = sum([ask[1] for ask in order_book['asks']])
        if bid_volume + ask_volume < 10000:  # Arbitrary threshold for significant depth
            log(f"[{symbol}] Low order book depth", level='WARNING')
            return False

        log(f"[{symbol}] Whale activity detected: volume={quote_volume}, depth={bid_volume + ask_volume}")
        return True

    except Exception as e:
        log(f"[{symbol}] Error in whale_check: {e}", level='ERROR')
        return False
