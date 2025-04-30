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
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn
import logging
import sys

# Setup logging to file for crash debugging
logging.basicConfig(
    filename="logs/crash.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
crash_logger = logging.getLogger()

app = FastAPI()
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")
templates = Jinja2Templates(directory="dashboard/templates")

@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy"})

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    signals = []
    try:
        with open("logs/signals_log.csv", "r") as file:
            lines = file.readlines()[-50:]  # Last 50 signals
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

crash_logger.info("Starting application")
try:
    port = int(os.getenv("PORT", 8000))
    crash_logger.info(f"Using port: {port}")
    threading.Thread(target=lambda: uvicorn.run(app, host="0.0.0.0", port=port, log_level="info"), daemon=True).start()
    log(f"✅ FastAPI server started on port {port}")
    crash_logger.info(f"FastAPI server started on port {port}")
except Exception as e:
    log(f"❌ Failed to start FastAPI server: {e}")
    crash_logger.error(f"Failed to start FastAPI server: {e}")
    sys.exit(1)

try:
    crash_logger.info("Initializing Binance exchange")
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'},
        'apiKey': os.getenv("BINANCE_API_KEY"),
        'secret': os.getenv("BINANCE_API_SECRET")
    })
    log("✅ Binance exchange initialized")
    crash_logger.info("Binance exchange initialized")
except Exception as e:
    log(f"❌ Failed to initialize Binance exchange: {e}")
    crash_logger.error(f"Failed to initialize Binance exchange: {e}")
    sys.exit(1)

try:
    crash_logger.info("Loading markets")
    markets = exchange.load_markets()
    symbols = [
        s['symbol'] for s in sorted(markets.values(), key=lambda x: x.get('info', {}).get('volume', 0), reverse=True)
        if s['quote'] == 'USDT' and s['active'] and s['symbol'] in exchange.symbols
        and not any(x in s['symbol'] for x in ["UP/USDT", "DOWN/USDT", "BULL", "BEAR", "3S", "3L", "5S", "5L"])
        and s.get('info', {}).get('volume', 0) > 1000000
    ][:15]  # Top 15 symbols
    log(f"✅ Loaded {len(symbols)} USDT symbols")
    crash_logger.info(f"Loaded {len(symbols)} USDT symbols")
except Exception as e:
    log(f"❌ Failed to load markets: {e}")
    crash_logger.error(f"Failed to load markets: {e}")
    sys.exit(1)

blacklisted_symbols = ["NKN/USDT", "ARPA/USDT", "HBAR/USDT", "STX/USDT", "KAVA/USDT"]
symbols = [s for s in symbols if s not in blacklisted_symbols]
MIN_VOLUME = 10000000
sent_signals = {}

while True:
    log("🔁 New Scan Cycle Started")
    crash_logger.info("New scan cycle started")
    for symbol in symbols:
        try:
            time.sleep(0.5)  # 0.5 second delay between symbols
            if symbol not in exchange.symbols:
                log(f"⚠️ Symbol {symbol} not found in exchange")
                crash_logger.warning(f"Symbol {symbol} not found in exchange")
                continue

            ticker = exchange.fetch_ticker(symbol)
            if not ticker or ticker.get("baseVolume", 0) < MIN_VOLUME:
                log(f"⚠️ Low volume for {symbol}: {ticker.get('baseVolume', 0)}")
                crash_logger.warning(f"Low volume for {symbol}: {ticker.get('baseVolume', 0)}")
                continue

            result = multi_timeframe_analysis(symbol, exchange)
            if not result:
                log(f"⚠️ No valid signal for {symbol}")
                crash_logger.warning(f"No valid signal for {symbol}")
                continue

            signal = result
            signal['prediction'] = predict_trend(symbol, exchange)
            if signal["prediction"] not in ["LONG", "SHORT"]:
                log(f"⚠️ Invalid prediction for {symbol}: {signal['prediction']}")
                crash_logger.warning(f"Invalid prediction for {symbol}: {signal['prediction']}")
                continue

            signal["leverage"] = 10  # Default leverage

            price = signal["price"]
            signal["tp1_possibility"] = round(max(70, 100 - abs(signal["tp1"] - price) / price * 100) if price != 0 else 70, 2)
            signal["tp2_possibility"] = round(max(60, 95 - abs(signal["tp2"] - price) / price * 100) if price != 0 else 60, 2)
            signal["tp3_possibility"] = round(max(50, 90 - abs(signal["tp3"] - price) / price * 100) if price != 0 else 50, 2)

            send_signal(signal)
            log_signal_to_csv(signal)
            sent_signals[symbol] = time.time()
            log(f"✅ Signal sent for {symbol}: TP1={signal['tp1']} ({signal['tp1_possibility']}%), TP2={signal['tp2']} ({signal['tp2_possibility']}%), TP3={signal['tp3']} ({signal['tp3_possibility']}%)")
            crash_logger.info(f"Signal sent for {symbol}: TP1={signal['tp1']} ({signal['tp1_possibility']}%), TP2={signal['tp2']} ({signal['tp2_possibility']}%), TP3={signal['tp3']} ({signal['tp3_possibility']}%)")

        except Exception as e:
            log(f"❌ Error with {symbol}: {e}")
            crash_logger.error(f"Error with {symbol}: {e}")
            continue

    update_signal_status()
    time.sleep(300)  # 5 minute interval
