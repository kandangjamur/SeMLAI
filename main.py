import os
import time
import threading
import ccxt
import numpy as np
from core.analysis import multi_timeframe_analysis
from core.engine import run_full_engine
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
MIN_VOLUME = 1000000

while True:
    log("🔁 New Scan Cycle Started")
    for symbol in symbols:
        try:
            if symbol not in exchange.symbols:
                continue

            ticker = exchange.fetch_ticker(symbol)
            if ticker.get("baseVolume", 0) < MIN_VOLUME:
                continue

            signal = multi_timeframe_analysis(symbol, exchange)
            if not signal:
                continue

            final_signal = run_full_engine(signal, symbol, exchange)

            if final_signal:
                send_signal(final_signal)
                log_signal_to_csv(final_signal)
                sent_signals[symbol] = time.time()
                log(f"✅ Signal Sent: {symbol} | {final_signal['trade_type']} | {final_signal['confidence']}%")

        except Exception as e:
            log(f"❌ Error with {symbol}: {e}")

    update_signal_status()
    time.sleep(120)
