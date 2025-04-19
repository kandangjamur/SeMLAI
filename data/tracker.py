import pandas as pd
import ccxt
import time
from utils.logger import log

def update_signal_status():
    try:
        exchange = ccxt.binance()
        df = pd.read_csv("logs/signals_log.csv")
        df['status'] = df.get('status', 'OPEN')

        for idx, row in df.iterrows():
            if row['status'] != 'OPEN':
                continue

            symbol = row['symbol']
            market = symbol.replace("/", "")
            price = exchange.fetch_ticker(symbol)['last']

            if row['prediction'] == "LONG":
                if price >= row['tp3']:
                    status = "HIT TP3"
                elif price >= row['tp2']:
                    status = "HIT TP2"
                elif price >= row['tp1']:
                    status = "HIT TP1"
                elif price <= row['sl']:
                    status = "SL HIT"
                else:
                    status = "OPEN"
            else:  # SHORT
                if price <= row['tp3']:
                    status = "HIT TP3"
                elif price <= row['tp2']:
                    status = "HIT TP2"
                elif price <= row['tp1']:
                    status = "HIT TP1"
                elif price >= row['sl']:
                    status = "SL HIT"
                else:
                    status = "OPEN"

            df.at[idx, 'status'] = status

        df.to_csv("logs/signals_log.csv", index=False)
        log("✅ TP/SL tracker updated.")

    except Exception as e:
        log(f"❌ TP/SL Tracking Error: {e}")
