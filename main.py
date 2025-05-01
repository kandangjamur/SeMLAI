import os
import time
import json
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
from datetime import datetime, timedelta
import psutil
import pandas as pd

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
                        "tp1_possibility": float(parts[10]) if len(parts) > 10 and parts[10] else 0,
                        "tp2_possibility": float(parts[11]) if len(parts) > 11 and parts[11] else 0,
                        "tp3_possibility": float(parts[12]) if len(parts) > 12 and parts[12] else 0
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
        ][:6]  # Reduced to 6 to stabilize instance
        log(f"✅ Loaded {len(symbols)} USDT symbols")
        crash_logger.info(f"Loaded {len(symbols)} USDT symbols")
        return symbols
    except Exception as e:
        log(f"❌ Failed to load markets: {e}")
        crash_logger.error(f"Failed to load markets: {e}")
        return []

def load_sent_signals():
    try:
        with open("logs/sent_signals.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        log(f"❌ Error loading sent_signals: {e}")
        crash_logger.error(f"Error loading sent_signals: {e}")
        return {}

def save_sent_signals(sent_signals):
    try:
        with open("logs/sent_signals.json", "w") as f:
            json.dump(sent_signals, f)
    except Exception as e:
        log(f"❌ Error saving sent_signals: {e}")
        crash_logger.error(f"Error saving sent_signals: {e}")

async def get_last_direction(symbol, exchange):
    try:
        if not os.path.exists("logs/signals_log.csv"):
            return None
        df = pd.read_csv("logs/signals_log.csv")
        df = df[df["symbol"] == symbol]
        if df.empty:
            return None
        last_row = df.iloc[-1]
        direction = last_row["direction"]
        tp1 = float(last_row["tp1"])
        tp2 = float(last_row["tp2"])
        tp3 = float(last_row["tp3"])
        sl = float(last_row["sl"])
        entry_price = float(last_row["price"])
        timestamp = pd.to_datetime(last_row["timestamp"]).timestamp()

        # Check trade status
        ticker = await exchange.fetch_ticker(symbol)
        current_price = ticker["last"]
        time_elapsed = time.time() - timestamp

        # Trade is closed if TP1/TP2/TP3 or SL hit, or 5 hours elapsed
        if direction == "LONG":
            if current_price >= tp1 or current_price >= tp2 or current_price >= tp3 or current_price <= sl or time_elapsed >= 5 * 3600:
                return None  # Trade closed
        elif direction == "SHORT":
            if current_price <= tp1 or current_price <= tp2 or current_price <= tp3 or current_price >= sl or time_elapsed >= 5 * 3600:
                return None  # Trade closed
        return direction, tp1, entry_price
    except Exception as e:
        log(f"❌ Error checking last direction for {symbol}: {e}")
        crash_logger.error(f"Error checking last direction for {symbol}: {e}")
        return None

async def process_symbol(symbol, exchange, CONFIDENCE_THRESHOLD, sent_signals, current_date, processed_symbols):
    try:
        # Check for duplicate processing
        if symbol in processed_symbols:
            log(f"⚠️ Skipping {symbol}: Already processed in this cycle")
            crash_logger.warning(f"Skipping {symbol}: Already processed in this cycle")
            return None

        # Check if signal was sent today
        if symbol in sent_signals and sent_signals[symbol]["date"] == current_date:
            log(f"⚠️ Skipping {symbol}: Already sent signal today")
            crash_logger.warning(f"Skipping {symbol}: Already sent signal today")
            return None

        await asyncio.sleep(0.4)  # Increased delay to prevent API rate limit
        if symbol not in exchange.symbols:
            log(f"⚠️ Symbol {symbol} not found in exchange")
            crash_logger.warning(f"Symbol {symbol} not found in exchange")
            return None

        ticker = await exchange.fetch_ticker(symbol)
        if not ticker or ticker.get("baseVolume", 0) < 1000000:
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
            signal['prediction'] = "LONG"

        # Check if previous trade is still active
        last_info = await get_last_direction(symbol, exchange)
        if last_info:
            last_dir, tp1, entry_price = last_info
            if last_dir == "LONG" and signal["prediction"] == "SHORT":
                log(f"⚠️ SHORT blocked for {symbol}: LONG still active (TP1={tp1})")
                crash_logger.warning(f"SHORT blocked for {symbol}: LONG still active (TP1={tp1})")
                return None
            if last_dir == "SHORT" and signal["prediction"] == "LONG":
                log(f"⚠️ LONG blocked for {symbol}: SHORT still active (TP1={tp1})")
                crash_logger.warning(f"LONG blocked for {symbol}: SHORT still active (TP1={tp1})")
                return None

        confidence = signal.get("confidence", 0)
        if confidence < CONFIDENCE_THRESHOLD:
            log(f"⚠️ No strong signals for {symbol}: confidence={confidence}")
            crash_logger.warning(f"No strong signals for {symbol}: confidence={confidence}")
            return None

        signal["leverage"] = 10
        signal["direction"] = signal["prediction"]
        price = signal["price"]
        v = max(0.5, min(2.0, confidence / 50))
        signal["tp1_possibility"] = round(min(95, 100 - (abs(signal["tp1"] - price) / price * 100) * v), 2)
        signal["tp2_possibility"] = round(min(85, 95 - (abs(signal["tp2"] - price) / price * 100) * v * 1.2), 2)
        signal["tp3_possibility"] = round(min(75, 90 - (abs(signal["tp3"] - price) / price * 100) * v * 1.5), 2)

        await send_signal(symbol, signal)
        log_signal_to_csv(signal)
        sent_signals[symbol] = {
            "date": current_date,
            "timestamp": time.time(),
            "direction": signal["prediction"]
        }
        save_sent_signals(sent_signals)
        log(f"✅ Signal sent for {symbol}: {signal['prediction']}, TP1={signal['tp1']} ({signal['tp1_possibility']}%), TP2={signal['tp2']} ({signal['tp2_possibility']}%), TP3={signal['tp3']} ({signal['tp3_possibility']}%)")
        crash_logger.info(f"Signal sent for {symbol}: {signal['prediction']}, TP1={signal['tp1']} ({signal['tp1_possibility']}%), TP2={signal['tp2']} ({signal['tp2_possibility']}%), TP3={signal['tp3']} ({signal['tp3_possibility']}%)")
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
            await exchange.close()
            sys.exit(1)

        blacklisted = ["NKN/USDT", "ARPA/USDT", "HBAR/USDT", "STX/USDT", "KAVA/USDT", "JST/USDT"]
        symbols = [s for s in symbols if s not in blacklisted]
        sent_signals = load_sent_signals()
        CONFIDENCE_THRESHOLD = 45  # Balanced for accuracy and signal count

        while True:
            current_date = datetime.utcnow().date().isoformat()
            sent_signals = {k: v for k, v in sent_signals.items() if v["date"] == current_date}
            save_sent_signals(sent_signals)

            memory = psutil.Process().memory_info().rss / 1024 / 1024
            log(f"🛠️ Memory usage: {memory:.2f} MB")
            crash_logger.info(f"Memory usage: {memory:.2f} MB")
            log("🔁 New Scan Cycle Started")
            crash_logger.info("New scan cycle started")

            processed_symbols = set()
            tasks = [
                process_symbol(symbol, exchange, CONFIDENCE_THRESHOLD, sent_signals, current_date, processed_symbols)
                for symbol in symbols
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for symbol, result in zip(symbols, results):
                if result and isinstance(result, dict):
                    sent_signals[symbol] = {
                        "date": current_date,
                        "timestamp": time.time(),
                        "direction": result["prediction"]
                    }
                    save_sent_signals(sent_signals)
                processed_symbols.add(symbol)
                log(f"🛠️ Processed symbols: {processed_symbols}")
                crash_logger.info(f"Processed symbols: {processed_symbols}")

            await update_signal_status()
            await exchange.close()
            exchange = await initialize_binance()
            await asyncio.sleep(240)
    except Exception as e:
        log(f"❌ Main loop error: {e}")
        crash_logger.error(f"Main loop error: {e}")
        sys.exit(1)
    finally:
        if 'exchange' in locals():
            await exchange.close()

@app.on_event("startup")
async def start_background_loop():
    asyncio.create_task(main_loop())

if __name__ == "__main__":
    log("Starting CryptoSniper application")
    crash_logger.info("Starting CryptoSniper application")
