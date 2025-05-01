analsys.py/import numpy as np
from core.indicators import calculate_indicators
from utils.logger import log

TIMEFRAMES = ["15m", "1h", "4h", "1d"]

async def multi_timeframe_analysis(symbol, exchange):
    timeframe_results = []

    for tf in TIMEFRAMES:
        try:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
            if not ohlcv or len(ohlcv) < 50:
                log(f"⚠️ Insufficient data for {symbol} on {tf}: {len(ohlcv)} candles")
                continue

            signal = calculate_indicators(symbol, ohlcv)
            if signal and not np.isnan(signal.get('confidence', 0)) and not np.isnan(signal.get('price', 0)):
                signal["timeframe"] = tf
                timeframe_results.append(signal)
            else:
                log(f"⚠️ Invalid signal for {symbol} on {tf}")
        except Exception as e:
            log(f"❌ Error in {symbol} on {tf}: {e}")
            continue

    strong = [s for s in timeframe_results if s['confidence'] >= 50]

    if len(strong) >= 3:
        prices = [s["price"] for s in strong]
        types = set([s["trade_type"] for s in strong])
        avg_conf = np.mean([s["confidence"] for s in strong])

        if max(prices) - min(prices) > min(prices) * 0.02:
            log(f"⚠️ Price deviation too high for {symbol} across timeframes")
            return None

        if len(types) > 1:
            log(f"⚠️ Inconsistent trade types for {symbol}: {types}")
            return None

        best_signal = max(strong, key=lambda s: s["confidence"])
        best_signal["confidence"] = round(avg_conf, 2)
        log(f"✅ Strong multi-timeframe signal for {symbol} with avg confidence {avg_conf}")
        return best_signal

    log(f"⚠️ No consistent strong signals for {symbol}")
    return None/ engine.py/from utils.logger import log

async def predict_trend(symbol, exchange):
    try:
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe="15m", limit=50)
        if len(ohlcv) < 3:
            log(f"⚠️ Insufficient data for trend prediction for {symbol}")
            return None

        closes = [x[4] for x in ohlcv]
        if closes[-1] > closes[-2] > closes[-3]:
            log(f"✅ LONG trend detected for {symbol}")
            return "LONG"
        elif closes[-1] < closes[-2] < closes[-3]:
            log(f"✅ SHORT trend detected for {symbol}")
            return "SHORT"

        log(f"⚠️ No clear trend for {symbol}")
        return None
    except Exception as e:
        log(f"❌ Error predicting trend for {symbol}: {e}")
        return None/ tracker.py/import pandas as pd
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
