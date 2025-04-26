import pandas as pd
import ccxt
from utils.logger import log

def update_signal_status():
    try:
        df = pd.read_csv("logs/signals_log.csv")
        exchange = ccxt.binance()
        updated = False

        for index, row in df.iterrows():
            if row["status"] != "pending":
                continue

            ticker = exchange.fetch_ticker(row["symbol"])
            high = ticker.get("high", 0)
            low = ticker.get("low", 0)

            if row["tp3"] <= high:
                df.at[index, "status"] = "tp3"
                updated = True
            elif row["tp2"] <= high:
                df.at[index, "status"] = "tp2"
                updated = True
            elif row["tp1"] <= high:
                df.at[index, "status"] = "tp1"
                updated = True
            elif row["sl"] >= low:
                df.at[index, "status"] = "sl"
                updated = True

        if updated:
            df.to_csv("logs/signals_log.csv", index=False)
            log("📈 Signal status updated.")
    except Exception as e:
        log(f"❌ Tracker Error: {e}")
