# main.py
import os
import time
import threading
import ccxt
import numpy as np
from core.indicators import calculate_indicators
from core.engine import predict_trend
from utils.logger import log, log_signal_to_csv
from telebot.bot import send_signal
from data.tracker import update_signal_status
from fastapi import FastAPI
import uvicorn

# Fake server to keep Koyeb happy
app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "running"}

def start_fake_server():
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Start server in background
threading.Thread(target=start_fake_server, daemon=True).start()

# Exchange setup
exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

# Timeframes to check
TIMEFRAMES = ["15m", "1h", "4h", "1d"]

# Get all USDT pairs
symbols = [
    s['symbol'] for s in exchange.load_markets().values()
    if s['quote'] == 'USDT' and not s['symbol'].endswith('UP/USDT') and not s['symbol'].endswith('DOWN/USDT')
]

sent_signals = {}

while True:
    log("🔁 New Scan Cycle")
    for symbol in symbols:
        try:
            if symbol not in exchange.symbols:
                log(f"⛔ Skipping {symbol} - Symbol not available on Binance")
                continue

            log(f"🔍 Scanning: {symbol}")
            ticker = exchange.fetch_ticker(symbol)
            if ticker.get("baseVolume", 0) < 120000:
                log(f"⚠️ Skipped {symbol} - Low volume")
                continue

            timeframe_results = []

            for tf in TIMEFRAMES:
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
                    if not ohlcv or len(ohlcv) < 50:
                        log(f"⚠️ Insufficient data for {symbol} on {tf}")
                        continue

                    signal = calculate_indicators(symbol, ohlcv)

                    if signal:
                        if np.isnan(signal.get("confidence", 0)) or np.isnan(signal.get("price", 0)):
                            log(f"⚠️ Skipped {symbol} invalid data on {tf}")
                            continue

                        timeframe_results.append(signal)

                except Exception as tf_error:
                    log(f"❌ Error fetching {symbol} on {tf}: {tf_error}")

            # Now check how many timeframes are strong
            strong_timeframes = [s for s in timeframe_results if s['confidence'] >= 75]

            if len(strong_timeframes) >= 3:
                main_signal = strong_timeframes[0]  # pick the first strong timeframe

                direction = predict_trend(symbol, ohlcv)
                main_signal["prediction"] = direction

                price = main_signal["price"]
                main_signal["tp1_possibility"] = round(max(70, 100 - abs(main_signal["tp1"] - price) / price * 100), 2)
                main_signal["tp2_possibility"] = round(max(60, 95 - abs(main_signal["tp2"] - price) / price * 100), 2)
                main_signal["tp3_possibility"] = round(max(50, 90 - abs(main_signal["tp3"] - price) / price * 100), 2)

                main_signal["confidence"] = min(main_signal["confidence"], 100)

                log_signal_to_csv(main_signal)
                send_signal(main_signal)
                sent_signals[symbol] = time.time()
                log(f"✅ Signal sent: {symbol} ({main_signal['confidence']}%)")

            else:
                log(f"⏭️ Skipped {symbol} - Not enough confirmations ({len(strong_timeframes)}/4)")

        except Exception as e:
            log(f"❌ Error for {symbol}: {e}")

    update_signal_status()
    time.sleep(120)
