import pandas as pd
import ccxt
import os
from utils.logger import log

def update_signal_status():
    path = "logs/signals_log.csv"
    if not os.path.exists(path):
        return

    exchange = ccxt.binance()
    df = pd.read_csv(path)
    updated = False

    for i in df.index:
        try:
            row = df.loc[i]
            if row["status"] != "active":
                continue

            symbol = row["symbol"]
            entry = float(row["price"])
            tp1 = float(row["tp1"])
            tp2 = float(row["tp2"])
            tp3 = float(row["tp3"])
            sl = float(row["sl"])

            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']

            if entry < tp1 < current_price:
                df.at[i, "status"] = "tp1"
                updated = True
            elif entry < tp2 < current_price:
                df.at[i, "status"] = "tp2"
                updated = True
            elif entry < tp3 < current_price:
                df.at[i, "status"] = "tp3"
                updated = True
            elif current_price < sl:
                df.at[i, "status"] = "sl"
                updated = True
        except Exception as e:
            log(f"[Tracker Error] {e}")

    if updated:
        df.to_csv(path, index=False)
