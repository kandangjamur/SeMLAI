import pandas as pd
import ccxt
from datetime import datetime
from utils.logger import log

def update_signal_status():
    try:
        df = pd.read_csv("logs/signals_log.csv")
        exchange = ccxt.binance()

        for i in range(len(df)):
            row = df.iloc[i]
            if row["status"] != "OPEN":
                continue

            symbol = row["symbol"]
            market_price = exchange.fetch_ticker(symbol)["last"]

            hit = ""
            if row["prediction"] == "LONG":
                if market_price >= row["tp3"]:
                    hit = "TP3"
                elif market_price >= row["tp2"]:
                    hit = "TP2"
                elif market_price >= row["tp1"]:
                    hit = "TP1"
                elif market_price <= row["sl"]:
                    hit = "SL"
            elif row["prediction"] == "SHORT":
                if market_price <= row["tp3"]:
                    hit = "TP3"
                elif market_price <= row["tp2"]:
                    hit = "TP2"
                elif market_price <= row["tp1"]:
                    hit = "TP1"
                elif market_price >= row["sl"]:
                    hit = "SL"

            if hit:
                df.at[i, "status"] = hit
                df.at[i, "closed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log(f"🔄 {symbol} → {hit} hit!")

        df.to_csv("logs/signals_log.csv", index=False)
    except Exception as e:
        log(f"❌ Tracker Error: {e}")
