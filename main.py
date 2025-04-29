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
from fastapi.responses import HTMLResponse
from fastapi.static_files import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from starlette.requests import Request

app = FastAPI()
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")
templates = Jinja2Templates(directory="dashboard/templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    signals = []
    try:
        with open("logs/signals_log.csv", "r") as file:
            lines = file.readlines()
            for line in lines[1:]:
                parts = line.strip().split(",")
                if len(parts) >= 10:
                    signals.append({
                        "symbol": parts[0],
                        "price": parts[1],
                        "direction": parts[2],
                        "tp1": parts[3],
                        "tp2": parts[4],
                        "tp3": parts[5],
                        "sl": parts[6],
                        "confidence": parts[7],
                        "trade_type": parts[8],
                        "timestamp": parts[9],
                        "tp1_possibility": parts[10] if len(parts) > 10 else 70,
                        "tp2_possibility": parts[11] if len(parts) > 11 else 60,
                        "tp3_possibility": parts[12] if len(parts) > 12 else 50
                    })
    except Exception as e:
        log(f"❌ Error reading signals log: {e}")
    return templates.TemplateResponse("dashboard.html", {"request": request, "signals": signals})

port = int(os.getenv("PORT", 8000))
threading.Thread(target=lambda: uvicorn.run(app, host="0.0.0.0", port=port, log_level="info"), daemon=True).start()

exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

markets = exchange.load_markets()
symbols = [
    s['symbol'] for s in markets.values()
    if s['quote'] == 'USDT' and s['active'] and s['symbol'] in exchange.symbols
    and not any(x in s['symbol'] for x in ["UP/USDT", "DOWN/USDT", "BULL", "BEAR", "3S", "3L", "5S", "5L"])
    and s.get('info', {}).get('volume', 0) > 1000000
]

blacklisted_symbols = ["NKN/USDT", "ARPA/USDT", "HBAR/USDT", "STX/USDT", "KAVA/USDT"]
symbols = [s for s in symbols if s not in blacklisted_symbols]

sent_signals = {}
MIN_VOLUME = 1000000

while True:
    log("🔁 New Scan Cycle Started")
    for symbol in symbols:
        try:
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
            signal["tp1_possibility"] = round(max(70, 100 - abs(signal["tp1"] - price) / price * 100) if price != 0 else 70, 2)
            signal["tp2_possibility"] = round(max(60, 95 - abs(signal["tp2"] - price) / price * 100) if price != 0 else 60, 2)
            signal["tp3_possibility"] = round(max(50, 90 - abs(signal["tp3"] - price) / price * 100) if price != 0 else 50, 2)

            send_signal(signal)
            log_signal_to_csv(signal)
            sent_signals[symbol] = time.time()
            log(f"✅ Signal sent for {symbol}: TP1={signal['tp1']} ({signal['tp1_possibility']}%), TP2={signal['tp2']} ({signal['tp2_possibility']}%), TP3={signal['tp3']} ({signal['tp3_possibility']}%)")

        except Exception as e:
            log(f"❌ Error with {symbol}: {e}")
            continue

    update_signal_status()
    time.sleep(120)
