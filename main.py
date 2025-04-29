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

app = FastAPI()

@app.get("/")
def root():
    return {"status": "running"}

threading.Thread(target=lambda: uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info"), daemon=True).start()

exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

# سمبلز کی لسٹ بنائیں، صرف درست USDT pairs
markets = exchange.load_markets()
symbols = [
    s['symbol'] for s in markets.values()
    if s['quote'] == 'USDT' and s['active'] and not any(x in s['symbol'] for x in ["UP/USDT", "DOWN/USDT", "BULL", "BEAR", "3S", "3L", "5S", "5L"])
    and s['symbol'] in exchange.symbols  # یقینی بنائیں کہ سمبل ایکسچینج پر موجود ہے
]

sent_signals = {}
MIN_VOLUME = 1000000

while True:
    log("🔁 New Scan Cycle Started")
    for symbol in symbols:
        try:
            # چیک کریں کہ سمبل درست ہے
            if symbol not in exchange.symbols:
                log(f"⚠️ Symbol {symbol} not found in exchange")
                continue

            ticker = exchange.fetch_ticker(symbol)
            if not ticker or ticker.get("baseVolume", 0) < MIN_VOLUME:
                log(f"⚠️ Low volume for {symbol}: {ticker.get('baseVolume', 0)}")
                continue

            result = multi_timeframe_analysis(symbol, exchange)
            if not result:
                log(f"⚠️ No valid signal for {symbol}")
                continue

            signal = result
            signal['prediction'] = predict_trend(symbol, exchange)
            if signal["prediction"] not in ["LONG", "SHORT"]:
                log(f"⚠️ Invalid prediction for {symbol}: {signal['prediction']}")
                continue

            try:
                leverage_info = exchange.fetch_leverage_tiers(symbol)
                signal["leverage"] = int(min(leverage_info[symbol][0]['maxLeverage'], signal.get("leverage", 20)))
            except Exception as e:
                log(f"⚠️ Leverage fetch failed for {symbol}: {e}")
                signal["leverage"] = 20

            price = signal["price"]
            signal["tp1_possibility"] = round(max(70, 100 - abs(signal["tp1"] - price) / price * 100), 2)
            signal["tp2_possibility"] = round(max(60, 95 - abs(signal["tp2"] - price) / price * 100), 2)
            signal["tp3_possibility"] = round(max(50, 90 - abs(signal["tp3"] - price) / price * 100), 2)

            send_signal(signal)
            log_signal_to_csv(signal)
            sent_signals[symbol] = time.time()
            log(f"✅ Signal sent for {symbol}")

        except Exception as e:
            log(f"❌ Error with {symbol}: {e}")

    update_signal_status()
    time.sleep(120)
