import pandas as pd
import os
import ccxt
from utils.logger import log

def update_signal_status():
    path = "logs/signals_log.csv"
    if not os.path.exists(path):
        return

    try:
        df = pd.read_csv(path)
        exchange = ccxt.binance()
        updated = []

        for index, row in df.iterrows():
            if row.get("status") in ["tp1", "tp2", "tp3", "sl"]:
                continue

            symbol = row["symbol"]
            price = exchange.fetch_ticker(symbol)["last"]

            if row["prediction"] == "LONG":
                if price >= row["tp3"]:
                    df.at[index, "status"] = "tp3"
                elif price >= row["tp2"]:
                    df.at[index, "status"] = "tp2"
                elif price >= row["tp1"]:
                    df.at[index, "status"] = "tp1"
                elif price <= row["sl"]:
                    df.at[index, "status"] = "sl"
            elif row["prediction"] == "SHORT":
                if price <= row["tp3"]:
                    df.at[index, "status"] = "tp3"
                elif price <= row["tp2"]:
                    df.at[index, "status"] = "tp2"
                elif price <= row["tp1"]:
                    df.at[index, "status"] = "tp1"
                elif price >= row["sl"]:
                    df.at[index, "status"] = "sl"

            updated.append(symbol)

        df.to_csv(path, index=False)
        if updated:
            log(f"📈 Status updated for: {', '.join(updated)}")
    except Exception as e:
        log(f"❌ Tracker Error: {e}")
