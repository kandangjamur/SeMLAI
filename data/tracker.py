# data/tracker.py
import pandas as pd
import ccxt

def update_signal_status():
    try:
        df = pd.read_csv("logs/signals_log.csv")
        exchange = ccxt.binance()

        updated = []
        for i, row in df.iterrows():
            if row["status"] != "Open":
                continue
            symbol = row["symbol"]
            try:
                price = exchange.fetch_ticker(symbol)["last"]
                if price >= row["tp3"]:
                    status = "TP3 Hit"
                elif price >= row["tp2"]:
                    status = "TP2 Hit"
                elif price >= row["tp1"]:
                    status = "TP1 Hit"
                elif price <= row["sl"]:
                    status = "SL Hit"
                else:
                    status = "Open"
                df.at[i, "status"] = status
            except Exception:
                continue

        df.to_csv("logs/signals_log.csv", index=False)
    except Exception as e:
        print(f"[Tracker Error] {e}")
