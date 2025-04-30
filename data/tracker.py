import pandas as pd
import os
import ccxt.async_support as ccxt
from utils.logger import log

async def update_signal_status():
    filename = "logs/signals_log.csv"
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

    for index, row in df.iterrows():
        if row['status'] != 'pending':
            continue

        try:
            ticker = await exchange.fetch_ticker(row['symbol'])
            current_price = ticker['last']

            if row['direction'] == 'LONG':
                if current_price >= row['tp1']:
                    df.at[index, 'status'] = 'TP1_hit'
                elif current_price <= row['sl']:
                    df.at[index, 'status'] = 'SL_hit'
            elif row['direction'] == 'SHORT':
                if current_price <= row['tp1']:
                    df.at[index, 'status'] = 'TP1_hit'
                elif current_price >= row['sl']:
                    df.at[index, 'status'] = 'SL_hit'

        except Exception as e:
            log(f"❌ Error updating status for {row['symbol']}: {e}")

    df.to_csv(filename, index=False)
    log("📝 Signal statuses updated")
