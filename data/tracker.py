import pandas as pd
import os
import ccxt.async_support as ccxt
from utils.logger import log
import json
from datetime import datetime

async def update_signal_status():
    filename = "logs/signals_log.csv"
    sent_signals_file = "logs/sent_signals.json"
    if not os.path.exists(filename):
        log("⚠️ No signals log file found")
        return

    df = pd.read_csv(filename)
    if df.empty:
        log("⚠️ Signals log is empty")
        return

    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })
    await exchange.load_markets()

    sent_signals = load_sent_signals()

    for index, row in df.iterrows():
        if row['status'] != 'pending':
            continue

        try:
            ticker = await exchange.fetch_ticker(row['symbol'])
            current_price = ticker['last']
            timestamp = pd.to_datetime(row['timestamp']).timestamp()
            time_elapsed = datetime.utcnow().timestamp() - timestamp

            if row['direction'] == 'LONG':
                if current_price >= row['tp3']:
                    df.at[index, 'status'] = 'TP3_hit'
                elif current_price >= row['tp2']:
                    df.at[index, 'status'] = 'TP2_hit'
                elif current_price >= row['tp1']:
                    df.at[index, 'status'] = 'TP1_hit'
                elif current_price <= row['sl']:
                    df.at[index, 'status'] = 'SL_hit'
                elif time_elapsed >= 5 * 3600:
                    df.at[index, 'status'] = 'timeout'
            elif row['direction'] == 'SHORT':
                if current_price <= row['tp3']:
                    df.at[index, 'status'] = 'TP3_hit'
                elif current_price <= row['tp2']:
                    df.at[index, 'status'] = 'TP2_hit'
                elif current_price <= row['tp1']:
                    df.at[index, 'status'] = 'TP1_hit'
                elif current_price >= row['sl']:
                    df.at[index, 'status'] = 'SL_hit'
                elif time_elapsed >= 5 * 3600:
                    df.at[index, 'status'] = 'timeout'

            if df.at[index, 'status'] in ['TP1_hit', 'TP2_hit', 'TP3_hit', 'SL_hit', 'timeout']:
                symbol = row['symbol']
                if symbol in sent_signals and sent_signals[symbol]["date"] == datetime.utcnow().date().isoformat():
                    del sent_signals[symbol]
                    save_sent_signals(sent_signals)
                    log(f"📝 Removed {symbol} from sent_signals due to trade closure: {df.at[index, 'status']}")

        except Exception as e:
            log(f"❌ Error updating status for {row['symbol']}: {e}")

    df.to_csv(filename, index=False)
    log("📝 Signal statuses updated")

def load_sent_signals():
    try:
        with open("logs/sent_signals.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        log(f"❌ Error loading sent_signals: {e}")
        return {}

def save_sent_signals(sent_signals):
    try:
        with open("logs/sent_signals.json", "w") as f:
            json.dump(sent_signals, f)
    except Exception as e:
        log(f"❌ Error saving sent_signals: {e}")
