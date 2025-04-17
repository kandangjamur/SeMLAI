import os
import ccxt
import json
import time
from datetime import datetime

def fetch_all_ohlcv():
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    symbols = [s for s in markets if '/USDT' in s and ':' not in s]

    timeframes = ['15m', '1h', '4h']
    os.makedirs("data/historical", exist_ok=True)

    for symbol in symbols:
        symbol_safe = symbol.replace("/", "_")
        all_timeframes_data = {}

        for tf in timeframes:
            try:
                candles = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
                all_timeframes_data[tf] = candles
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Fetched {symbol} - {tf}")
                time.sleep(0.1)  # Prevent rate limit
            except Exception as e:
                print(f"[ERROR] {symbol} - {tf}: {e}")

        if all_timeframes_data:
            with open(f"data/historical/{symbol_safe}.json", "w") as f:
                json.dump(all_timeframes_data, f)

if __name__ == "__main__":
    fetch_all_ohlcv()
