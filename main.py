# main.py
import os
import time
import threading
import ccxt
import numpy as np
from core.analysis import multi_timeframe_analysis
from core.engine import predict_trend
from utils.logger import log, log_signal_to_csv
from telebot.bot import send_signal
from data.tracker import update_signal_status
from fastapi import FastAPI
import uvicorn

# Fake server for Koyeb
app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "running"}

def start_fake_server():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

threading.Thread(target=start_fake_server, daemon=True).start()

# Setup exchange
exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

markets = exchange.load_markets()
symbols = [
    s['symbol'] for s in markets.values()
    if s['quote'] == 'USDT' and not any(x in s['symbol'] for x in ["UP/USDT", "DOWN/USDT", "BULL", "BEAR", "3S", "3L", "5S", "5L"])
]

sent_signals = {}
MIN_VOLUME = 1000000  # 1M USDT

while True:
    log("🔁 New Scan Cycle Started")
    for symbol in symbols:
        try:
            if symbol not in exchange.symbols:
                log(f"⛔ {symbol} not found on exchange. Skipping.")
                continue

            ticker = exchange.fetch_ticker(symbol)
            if ticker.get("baseVolume", 0) < MIN_VOLUME:
                log(f"⚠️ {symbol} skipped due to low volume ({ticker.get('baseVolume', 0)})")
                continue

            result = multi_timeframe_analysis(symbol, exchange)
            if not result:
                continue

            signal = result
            signal['prediction'] = predict_trend(symbol, exchange)

            if signal["prediction"] not in ["LONG", "SHORT"]:
                log(f"⚠️ {symbol} has no strong direction. Skipping.")
                continue

            # Real leverage limit fetch
            try:
                leverage_info = exchange.fetch_leverage_tiers(symbol)
                max_leverage = leverage_info[symbol][0]['maxLeverage']
                signal["leverage"] = int(min(max_leverage, signal.get("leverage", 20)))
            except Exception:
                signal["leverage"] = 20

            price = signal["price"]
            signal["tp1_possibility"] = round(max(70, 100 - abs(signal["tp1"] - price) / price * 100), 2)
            signal["tp2_possibility"] = round(max(60, 95 - abs(signal["tp2"] - price) / price * 100), 2)
            signal["tp3_possibility"] = round(max(50, 90 - abs(signal["tp3"] - price) / price * 100), 2)

            log_signal_to_csv(signal)
            send_signal(signal)
            sent_signals[symbol] = time.time()

            log(f"✅ Signal Sent: {symbol} | {signal['trade_type']} | {signal['confidence']}% confidence")

        except Exception as e:
            log(f"❌ Error with {symbol}: {e}")

    update_signal_status()
    time.sleep(120)
