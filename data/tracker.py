import pandas as pd
import ccxt
from utils.logger import log

def update_signal_status():
    try:
        df = pd.read_csv("logs/signals_log.csv")
        exchange = ccxt.binance()
        for i, row in df.iterrows():
            if row['status'] != 'open':
                continue
            try:
                price = exchange.fetch_ticker(row['symbol'])['last']
                if row['prediction'] == "LONG":
                    if price >= row['tp3']:
                        df.at[i, 'status'] = 'tp3'
                    elif price >= row['tp2']:
                        df.at[i, 'status'] = 'tp2'
                    elif price >= row['tp1']:
                        df.at[i, 'status'] = 'tp1'
                    elif price <= row['sl']:
                        df.at[i, 'status'] = 'sl'
                else:  # SHORT
                    if price <= row['tp3']:
                        df.at[i, 'status'] = 'tp3'
                    elif price <= row['tp2']:
                        df.at[i, 'status'] = 'tp2'
                    elif price <= row['tp1']:
                        df.at[i, 'status'] = 'tp1'
                    elif price >= row['sl']:
                        df.at[i, 'status'] = 'sl'
            except:
                continue
        df.to_csv("logs/signals_log.csv", index=False)
        log("📊 TP/SL tracker updated.")
    except Exception as e:
        log(f"❌ Tracker error: {e}")
