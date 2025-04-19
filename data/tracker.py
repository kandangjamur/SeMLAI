import pandas as pd
import ccxt
import os
from datetime import datetime
from utils.logger import log

def update_signal_status():
    try:
        if not os.path.exists("logs/signals_log.csv"):
            log("⚠️ No log file to update.")
            return

        df = pd.read_csv("logs/signals_log.csv")
        if "status" not in df.columns:
            df["status"] = "PENDING"

        exchange = ccxt.binance()
        for idx, row in df.iterrows():
            if row["status"] != "PENDING":
                continue
            symbol = row["symbol"]
            try:
                ticker = exchange.fetch_ticker(symbol)
                current_price = ticker["last"]
                if row["prediction"] == "LONG":
                    if current_price >= row["tp3"]:
                        df.at[idx, "status"] = "TP3"
                    elif current_price >= row["tp2"]:
                        df.at[idx, "status"] = "TP2"
                    elif current_price >= row["tp1"]:
                        df.at[idx, "status"] = "TP1"
                    elif current_price <= row["sl"]:
                        df.at[idx, "status"] = "SL"
                else:
                    if current_price <= row["tp3"]:
                        df.at[idx, "status"] = "TP3"
                    elif current_price <= row["tp2"]:
                        df.at[idx, "status"] = "TP2"
                    elif current_price <= row["tp1"]:
                        df.at[idx, "status"] = "TP1"
                    elif current_price >= row["sl"]:
                        df.at[idx, "status"] = "SL"
            except Exception as e:
                log(f"🔁 Error fetching {symbol} price: {e}")

        df.to_csv("logs/signals_log.csv", index=False)
        log("📈 Signal status updated.")
    except Exception as e:
        log(f"❌ Tracker error: {e}")
