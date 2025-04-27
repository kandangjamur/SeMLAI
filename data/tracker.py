import os
import pandas as pd
import ccxt
from utils.logger import log

def update_signal_status():
    try:
        if not os.path.exists("logs/signals_log.csv"):
            return

        df = pd.read_csv("logs/signals_log.csv")
        exchange = ccxt.binance()
        updated = False

        for idx, row in df.iterrows():
            if row["status"] != "pending":
                continue

            ticker = exchange.fetch_ticker(row["symbol"])
            high = ticker.get("high", 0)
            low = ticker.get("low", 0)

            if high >= row["tp3"]:
                df.at[idx, "status"] = "tp3"
                updated = True
            elif high >= row["tp2"]:
                df.at[idx, "status"] = "tp2"
                updated = True
            elif high >= row["tp1"]:
                df.at[idx, "status"] = "tp1"
                updated = True
            elif low <= row["sl"]:
                df.at[idx, "status"] = "sl"
                updated = True

        if updated:
            df.to_csv("logs/signals_log.csv", index=False)
            log("✅ Tracker Updated")
    except Exception as e:
        log(f"❌ Tracker Error: {e}")
