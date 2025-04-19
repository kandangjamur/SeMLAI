import ccxt
import pandas as pd
from utils.logger import log

def update_signal_status():
    exchange = ccxt.binance()
    try:
        df = pd.read_csv("logs/signals_log.csv")
        for i, row in df.iterrows():
            if row["status"] != "open":
                continue
            price = exchange.fetch_ticker(row["symbol"])["last"]
            if row["prediction"] == "LONG":
                if price >= row["tp3"]: status = "hit_tp3"
                elif price >= row["tp2"]: status = "hit_tp2"
                elif price >= row["tp1"]: status = "hit_tp1"
                elif price <= row["sl"]: status = "hit_sl"
                else: status = "open"
            else:  # SHORT
                if price <= row["tp3"]: status = "hit_tp3"
                elif price <= row["tp2"]: status = "hit_tp2"
                elif price <= row["tp1"]: status = "hit_tp1"
                elif price >= row["sl"]: status = "hit_sl"
                else: status = "open"

            df.at[i, "status"] = status

        df.to_csv("logs/signals_log.csv", index=False)
        log("📊 TP/SL tracker updated.")
    except Exception as e:
        log(f"❌ Tracker error: {e}")
