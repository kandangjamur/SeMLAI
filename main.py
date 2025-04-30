# main.py
import os
import time
import ccxt.async_support as ccxt
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
import logging
import sys
import asyncio

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
            lines = file.readlines()[-50:]
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
    except FileNotFoundError:
        log("⚠️ Signals log is empty")
    except Exception as e:
        log(f"❌ Error reading signals log: {e}")
        crash_logger.error(f"Error reading signals log: {e}")
    return templates.TemplateResponse("dashboard.html", {"request": request, "signals": signals})

async def initialize_binance():
    try:
        crash_logger.info("Initializing Binance exchange")
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'},
            'apiKey': os.getenv("BINANCE_API_KEY"),
            'secret': os.getenv("BINANCE_API_SECRET")
        })
        await exchange.load_markets()
        log("✅ Binance exchange initialized")
        crash_logger.info("Binance exchange initialized")
        return exchange
    except Exception as e:
        log(f"❌ Failed to initialize Binance exchange: {e}")
        crash_logger.error(f"Failed to initialize Binance exchange: {e}")
        sys.exit(1)

async def load_symbols(exchange):
    try:
        crash_logger.info("Loading markets")
        markets = exchange.markets
        invalid_symbols = ['TUSD/USDT', 'USDC/USDT']
        symbols = [
            s['symbol'] for s in markets.values()
            if s['quote'] == 'USDT' and s['active'] and s['symbol'] in exchange.symbols
            and not any(x in s['symbol'] for x in ["UP/USDT", "DOWN/USDT", "BULL", "BEAR", "3S", "3L", "5S", "5L"])
            and s['symbol'] not in invalid_symbols
        ][:15]
        log(f"✅ Loaded {len(symbols)} USDT symbols")
        crash_logger.info(f"Loaded {len(symbols)} USDT symbols")
        return symbols
    except Exception as e:
        log(f"❌ Failed to load markets: {e}")
        crash_logger.error(f"Failed to load markets: {e}")
        return []

async def main_loop():
    crash_logger.info("Starting main loop")
    exchange = await initialize_binance()
    symbols = await load_symbols(exchange)
    if not symbols:
        log("⚠️ No symbols loaded, exiting")
        crash_logger.warning("No symbols loaded, exiting")
        sys.exit(1)

    blacklisted_symbols = ["NKN/USDT", "ARPA/USDT", "HBAR/USDT", "STX/USDT", "KAVA/USDT"]
    symbols = [s for s in symbols if s not in blacklisted_symbols]
    MIN_VOLUME = 3000000
    sent_signals = {}
    CONFIDENCE_THRESHOLD = 50

    while True:
        log("🔁 New Scan Cycle Started")
        crash_logger.info("New scan cycle started")
        for symbol in symbols:
            try:
                await asyncio.sleep(0.5)
                if symbol not in exchange.symbols:
                    log(f"⚠️ Symbol {symbol} not found in exchange")
                    crash_logger.warning(f"Symbol {symbol} not found in exchange")
                    continue

                ticker = await exchange.fetch_ticker(symbol)
                if not ticker or ticker.get("baseVolume", 0) < MIN_VOLUME:
                    log(f"⚠️ Low volume for {symbol}: {ticker.get('baseVolume', 0)}")
                    crash_logger.warning(f"Low volume for {symbol}: {ticker.get('baseVolume', 0)}")
                    continue

                result = await multi_timeframe_analysis(symbol, exchange)
                if not result:
                    log(f"⚠️ No valid signal for {symbol}")
                    crash_logger.warning(f"No valid signal for {symbol}")
                    continue

                signal = result
                signal['prediction'] = await predict_trend(symbol, exchange)
                if signal["prediction"] not in ["LONG", "SHORT"]:
                    log(f"⚠️ Invalid prediction for {symbol}: {signal['prediction']}")
                    crash_logger.warning(f"Invalid prediction for {symbol}: {signal['prediction']}")
                    continue

                confidence = signal.get("confidence", 0)
                if confidence < CONFIDENCE_THRESHOLD:
                    log(f"⚠️ No strong signals for {symbol}: confidence={confidence}")
                    crash_logger.warning(f"No strong signals for {symbol}: confidence={confidence}")
                    continue

                await send_signal(symbol, signal)
                sent_signals[symbol] = signal

            except Exception as e:
                log(f"❌ Error in processing {symbol}: {e}")
                crash_logger.error(f"Error in processing {symbol}: {e}")
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main_loop())
