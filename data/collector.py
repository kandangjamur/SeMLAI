# 📁 data/collector.py

import ccxt
import os
import pandas as pd
import json
from datetime import datetime

exchange = ccxt.binance()

# ------------ CONFIGURATION ------------
TIMEFRAMES = ['15m', '1h', '4h']  # You can add '30m', '1d' etc.
DATA_LIMIT = 500  # Max candles per fetch
OUTPUT_FORMAT = 'csv'  # or 'json' or 'pandas'
SYMBOL_FILTER = '/USDT'  # only fetch for USDT pairs
# ---------------------------------------

def fetch_ohlcv(symbol, timeframe):
    try:
        return exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=DATA_LIMIT)
    except Exception as e:
        print(f"❌ Fetch error {symbol} ({timeframe}): {e}")
        return []

def save_to_csv(symbol, timeframe, df):
    folder = f"data/historical/{timeframe}"
    os.makedirs(folder, exist_ok=True)
    filename = os.path.join(folder, f"{symbol.replace('/', '_')}.csv")
    df.to_csv(filename, index=False)
    print(f"📁 Saved CSV: {filename}")

def save_to_json(symbol, timeframe, df):
    folder = f"data/historical/{timeframe}"
    os.makedirs(folder, exist_ok=True)
    filename = os.path.join(folder, f"{symbol.replace('/', '_')}.json")
    df.to_json(filename, orient="records")
    print(f"📁 Saved JSON: {filename}")

def collect_data():
    print(f"📊 Loading market pairs...")
    symbols = [s for s in exchange.load_markets() if SYMBOL_FILTER in s]
    print(f"✅ Found {len(symbols)} symbols to fetch.")

    for symbol in symbols:
        for tf in TIMEFRAMES:
            print(f"🔄 Fetching {symbol} ({tf})...")
            ohlcv = fetch_ohlcv(symbol, tf)
            if not ohlcv:
                continue

            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')

            if OUTPUT_FORMAT == 'csv':
                save_to_csv(symbol, tf, df)
            elif OUTPUT_FORMAT == 'json':
                save_to_json(symbol, tf, df)
            elif OUTPUT_FORMAT == 'pandas':
                print(df.head())  # You can return it for backtest
            else:
                print("❌ Unknown format!")

if __name__ == "__main__":
    collect_data()
