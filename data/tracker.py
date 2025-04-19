import pandas as pd
import os
from utils.logger import log
import ccxt

def update_signal_status():
    log("🔁 Updating signal status...")
    if not os.path.exists("logs/signals_log.csv"):
        log("⚠️ No signals_log.csv found.")
        return

    df = pd.read_csv("logs/signals_log.csv")
    if "status" not in df.columns:
        df["status"] = "open"

    exchange = ccxt.binance()

    for i, row in df[df["status"] == "open"].iterrows():
        symbol = row["symbol"]
        try:
            ticker = exchange.fetch_ticker(symbol)
            last_price = ticker["last"]

            if row["prediction"] == "LONG":
                if last_price >= row["tp3"]:
                    df.at[i, "status"] = "TP3"
                elif last_price >= row["tp2"]:
                    df.at[i, "status"] = "TP2"
                elif last_price >= row["tp1"]:
                    df.at[i, "status"] = "TP1"
                elif last_price <= row["sl"]:
                    df.at[i, "status"] = "SL"
            else:
                if last_price <= row["tp3"]:
                    df.at[i, "status"] = "TP3"
                elif last_price <= row["tp2"]:
                    df.at[i, "status"] = "TP2"
                elif last_price <= row["tp1"]:
                    df.at[i, "status"] = "TP1"
                elif last_price >= row["sl"]:
                    df.at[i, "status"] = "SL"
        except Exception as e:
            log(f"⚠️ Error updating {symbol}: {e}")
            continue

    df.to_csv("logs/signals_log.csv", index=False)
    log("✅ Signal tracking updated.")
