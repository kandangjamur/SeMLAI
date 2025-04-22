import pandas as pd
import os
import ccxt
from utils.logger import log

def update_signal_status():
    try:
        log("🔁 Updating signal status...")
        if not os.path.exists("logs/signals_log.csv"):
            log("⚠️ signals_log.csv not found.")
            return

        df = pd.read_csv("logs/signals_log.csv")
        if "status" not in df.columns:
            df["status"] = "open"

        exchange = ccxt.binance()
        for i, row in df[df["status"] == "open"].iterrows():
            try:
                ticker = exchange.fetch_ticker(row["symbol"])
                last_price = ticker["last"]
                status = "open"

                if row["prediction"] == "LONG":
                    if last_price >= row["tp3"]:
                        status = "tp3"
                    elif last_price >= row["tp2"]:
                        status = "tp2"
                    elif last_price >= row["tp1"]:
                        status = "tp1"
                    elif last_price <= row["sl"]:
                        status = "sl"
                else:  # SHORT
                    if last_price <= row["tp3"]:
                        status = "tp3"
                    elif last_price <= row["tp2"]:
                        status = "tp2"
                    elif last_price <= row["tp1"]:
                        status = "tp1"
                    elif last_price >= row["sl"]:
                        status = "sl"
                df.at[i, "status"] = status
            except Exception as e:
                log(f"⚠️ Tracker error for {row['symbol']}: {e}")
                continue

        df.to_csv("logs/signals_log.csv", index=False)
        log("✅ TP/SL tracker updated.")
    except Exception as e:
        log(f"❌ Tracker error: {e}")
