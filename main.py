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

# Logging setup
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
def health_check():
    return {"status": "healthy"}

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
                        "tp1_possibility": parts[10] if len(parts) > 10 else 85,
                        "tp2_possibility": parts[11] if len(parts) > 11 else 75,
                        "tp3_possibility": parts[12] if len(parts) > 12 else 65
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
        invalid_symbols = ['TUSD/USDT', 'USDC/USDT', 'BUSD/USDT', 'LUNA/USDT', 'WING/USDT']
        symbols = [
            s['symbol'] for s in markets.values()
            if s['quote'] == 'USDT' and s['active'] and s['symbol'] in exchange.symbols
            and not any(x in s['symbol'] for x in ["UP/USDT", "DOWN/USDT", "BULL", "BEAR", "3S", "3L", "5S", "5L"])
            and s['symbol'] not in invalid_symbols
        ][:15]  # 15 symbols for 60-70 signals/day
        log(f"✅ Loaded {len(symbols)} USDT symbols")
        crash_logger.info(f"Loaded {len(symbols)} USDT symbols")
        return symbols
    except Exception as e:
        log(f"❌ Failed to load markets: {e}")
        crash_logger.error(f"Failed to load markets: {e}")
        return []

async def process_symbol(symbol, exchange, CONFIDENCE_THRESHOLD):
    try:
        if symbol not in exchange.symbols:
            log(f"⚠️ Symbol {symbol} not found in exchange")
            crash_logger.warning(f"Symbol {symbol} not found in exchange")
            return None

        ticker = await exchange.fetch_ticker(symbol)
        if not ticker or ticker.get("baseVolume", 0) < 1000000:  # High volume for accuracy
            log(f"⚠️ Low volume for {symbol}: {ticker.get('baseVolume', 0)}")
            crash_logger.warning(f"Low volume for {symbol}: {ticker.get('baseVolume', 0)}")
            return None

        result = await multi_timeframe_analysis(symbol, exchange)
        if not result:
            log(f"⚠️ No valid signal for {symbol}")
            crash_logger.warning(f"No valid signal for {symbol}")
            return None

        signal = result
        signal['prediction'] = await predict_trend(symbol, exchange)
        if signal["prediction"] not in ["LONG", "SHORT"]:
            log(f"⚠️ Invalid prediction for {symbol}: {signal['prediction']}")
            crash_logger.warning(f"Invalid prediction for {symbol}: {signal['prediction']}")
            signal['prediction'] = "LONG"  # Default to LONG if None

        confidence = signal.get("confidence", 0)
        if confidence < CONFIDENCE_THRESHOLD:
            log(f"⚠️ No strong signals for {symbol}: confidence={confidence}")
            crash_logger.warning(f"No strong signals for {symbol}: confidence={confidence}")
            return None

        signal["leverage"] = 10
        price = signal["price"]
        signal["tp1_possibility"] = round(min(95, 100 - abs(signal["tp1"] - price) / price * 100) if price != 0 else 85, 2)
        signal["tp2_possibility"] = round(min(85, 95 - abs(signal["tp2"] - price) / price * 100) if price != 0 else 75, 2)
        signal["tp3_possibility"] = round(min(75, 90 - abs(signal["tp3"] - price) / price * 100) if price != 0 else 65, 2)

        await send_signal(symbol, signal)
        log_signal_to_csv(signal)
        log(f"✅ Signal sent for {symbol}: TP1={signal['tp1']} ({signal['tp1_possibility']}%), TP2={signal['tp2']} ({signal['tp2_possibility']}%), TP3={signal['tp3']} ({signal['tp3_possibility']}%)")
        crash_logger.info(f"Signal sent for {symbol}: TP1={signal['tp1']} ({signal['tp1_possibility']}%), TP2={signal['tp2']} ({signal['tp2_possibility']}%), TP3={signal['tp3']} ({signal['tp3_possibility']}%)")
        return signal

    except Exception as e:
        log(f"❌ Error with {symbol}: {e}")
        crash_logger.error(f"Error with {symbol}: {e}")
        return None

async def main_loop():
    crash_logger.info("Starting main loop")
    try:
        exchange = await initialize_binance()
        symbols = await load_symbols(exchange)
        if not symbols:
            log("⚠️ No symbols loaded, exiting")
            crash_logger.warning("No symbols loaded, exiting")
            sys.exit(1)

        blacklisted_symbols = ["NKN/USDT", "ARPA/USDT", "HBAR/USDT", "STX/USDT", "KAVA/USDT", "JST/USDT"]
        symbols = [s for s in symbols if s not in blacklisted_symbols]
        sent_signals = {}
        CONFIDENCE_THRESHOLD = 50  # High for accuracy
        MIN_CANDLES = 30  # Avoid insufficient data

        while True:
            log("🔁 New Scan Cycle Started")
            crash_logger.info("New scan cycle started")
            tasks = [process_symbol(symbol, exchange, CONFIDENCE_THRESHOLD) for symbol in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for symbol, result in zip(symbols, results):
                if result and isinstance(result, dict):
                    sent_signals[symbol] = time.time()

            update_signal_status()
            await asyncio.sleep(240)  # 4 minute interval for more cycles
    except Exception as e:
        log(f"❌ Main loop error: {e}")
        crash_logger.error(f"Main loop error: {e}")
        sys.exit(1)
    finally:
        if 'exchange' in locals():
            await exchange.close()

# FastAPI startup trigger
@app.on_event("startup")
async def start_background_loop():
    asyncio.create_task(main_loop())

if __name__ == "__main__":
    log("Starting CryptoSniper application")
    crash_logger.info("Starting CryptoSniper application")
