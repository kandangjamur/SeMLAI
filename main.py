import os
import time
import json
import ccxt.async_support as ccxt
import numpy as np
import pandas as pd
import asyncio
import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import psutil
from datetime import datetime, timedelta
from core.analysis import analyze_symbol
from core.engine import predict_trend
from utils.logger import log, log_signal_to_csv
from telebot.sender import send_telegram_signal
from data.tracker import update_signal_status
from telebot.report_generator import generate_daily_summary

app = FastAPI()
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")
templates = Jinja2Templates(directory="dashboard/templates")

CONFIDENCE_THRESHOLD = 70

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
        log("Signals log is empty")
    except Exception as e:
        log(f"Error reading signals log: {e}", level='ERROR')
    return templates.TemplateResponse("dashboard.html", {"request": request, "signals": signals})

async def initialize_binance():
    try:
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'},
            'apiKey': os.getenv("BINANCE_API_KEY"),
            'secret': os.getenv("BINANCE_API_SECRET")
        })
        await exchange.load_markets()
        log("Binance exchange initialized")
        return exchange
    except Exception as e:
        log(f"Failed to initialize Binance exchange: {e}", level='ERROR')
        return None

async def load_symbols(exchange):
    try:
        markets = exchange.markets
        symbols = []
        for s in markets.values():
            if (
                s['quote'] == 'USDT' and 
                s['active'] and 
                s['symbol'] in exchange.markets and
                not any(x in s['symbol'] for x in ["UP/USDT", "DOWN/USDT", "BULL", "BEAR", "3S", "3L", "5S", "5L"])
            ):
                try:
                    if exchange.has['fetchTicker']:
                        await exchange.fetch_ticker(s['symbol'])
                        symbols.append(s['symbol'])
                except Exception as e:
                    log(f"Skipping {s['symbol']}: {e}", level='INFO')
        log(f"Loaded {len(symbols)} valid USDT symbols")
        return symbols
    except Exception as e:
        log(f"Failed to load markets: {e}", level='ERROR')
        return []

def load_sent_signals():
    try:
        with open("logs/sent_signals.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        log(f"Error loading sent_signals: {e}", level='ERROR')
        return {}

def save_sent_signals(sent_signals):
    try:
        with open("logs/sent_signals.json", "w") as f:
            json.dump(sent_signals, f)
    except Exception as e:
        log(f"Error saving sent_signals: {e}", level='ERROR')

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

        ticker = await exchange.fetch_ticker(symbol)
        current_price = ticker["last"]
        time_elapsed = time.time() - timestamp

        # Check if TP1, TP2, TP3, SL hit or trade expired
        if direction == "LONG":
            if (
                current_price >= tp1 or 
                current_price >= tp2 or 
                current_price >= tp3 or 
                current_price <= sl or 
                time_elapsed >= 5 * 3600
            ):
                return None  # Trade completed or expired
        elif direction == "SHORT":
            if (
                current_price <= tp1 or 
                current_price <= tp2 or 
                current_price <= tp3 or 
                current_price >= sl or 
                time_elapsed >= 5 * 3600
            ):
                return None  # Trade completed or expired
        return direction, tp1, tp2, entry_price
    except Exception as e:
        log(f"Error checking last direction for {symbol}: {e}", level='ERROR')
        return None

async def process_symbol(symbol, exchange, sent_signals, current_date, processed_symbols, ticker_cache, ohlcv_cache):
    try:
        if symbol in processed_symbols:
            return None

        if symbol in sent_signals and sent_signals[symbol]["date"] == current_date:
            return None

        await asyncio.sleep(1.2)
        if symbol not in exchange.markets:
            return None

        if symbol in ticker_cache:
            ticker = ticker_cache[symbol]
        else:
            ticker = await exchange.fetch_ticker(symbol)
            ticker_cache[symbol] = ticker

        if not ticker or ticker.get("baseVolume", 0) < 50000:
            return None

        timeframe = "15m"  # Default for Scalp
        trade_type = "Scalp"
        if ticker.get("baseVolume", 0) < 100000 or signal.get("confidence", 0) < 90:
            timeframe = "1h"  # Normal trade
            trade_type = "Normal"

        if symbol in ohlcv_cache:
            ohlcv = ohlcv_cache[symbol]
        else:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=50)
            ohlcv_cache[symbol] = ohlcv

        result = await analyze_symbol(exchange, symbol)
        if not result or not result.get("signal"):
            return None

        signal = result
        signal["prediction"] = await predict_trend(symbol, exchange)
        if signal["prediction"] not in ["LONG", "SHORT"]:
            signal["prediction"] = signal["signal"]

        last_info = await get_last_direction(symbol, exchange)
        if last_info:
            last_dir, tp1, tp2, entry_price = last_info
            # Block new signal unless it's a reverse trade
            if last_dir == signal["prediction"]:
                return None  # Same direction, wait for TP1/TP2
            # Allow reverse trade only if TP1 or TP2 hit
            ticker = await exchange.fetch_ticker(symbol)
            current_price = ticker["last"]
            if last_dir == "LONG" and signal["prediction"] == "SHORT":
                if current_price < tp1 and current_price < tp2:
                    return None  # TP1/TP2 not hit, block reverse
            elif last_dir == "SHORT" and signal["prediction"] == "LONG":
                if current_price > tp1 and current_price > tp2:
                    return None  # TP1/TP2 not hit, block reverse

        confidence = min(signal.get("confidence", 0), 100)  # Cap confidence at 100
        tp1_possibility = signal.get("tp1_chance", 0)
        print(f"🔍 {symbol} | Confidence: {confidence:.2f} | Direction: {signal['prediction']} | TP1 Chance: {tp1_possibility:.2f} | Trade Type: {trade_type}")

        if confidence < CONFIDENCE_THRESHOLD:
            print("⚠️ Skipped - Low confidence")
            return None

        signal["leverage"] = 10
        signal["direction"] = signal["prediction"]
        signal["trade_type"] = trade_type
        price = ticker["last"]
        atr = signal.get("atr", 0.01)
        signal["price"] = price
        signal["tp1"] = round(price + atr * 1.2 if signal["direction"] == "LONG" else price - atr * 1.2, 4)
        signal["tp2"] = round(price + atr * 2.0 if signal["direction"] == "LONG" else price - atr * 2.0, 4)
        signal["tp3"] = round(price + atr * 3.0 if signal["direction"] == "LONG" else price - atr * 3.0, 4)
        signal["sl"] = round(price - atr * 0.8 if signal["direction"] == "LONG" else price + atr * 0.8, 4)
        signal["tp1_possibility"] = round(min(95, confidence + 5), 1)
        signal["tp2_possibility"] = round(min(85, confidence - 5), 1)
        signal["tp3_possibility"] = round(min(75, confidence - 15), 1)

        await send_telegram_signal(symbol, signal)
        log_signal_to_csv(signal)
        sent_signals[symbol] = {
            "date": current_date,
            "timestamp": time.time(),
            "direction": signal["prediction"],
            "trade_type": trade_type
        }
        save_sent_signals(sent_signals)
        log(f"Signal sent for {symbol}: {signal['prediction']}, TP1={signal['tp1']} ({signal['tp1_possibility']}%), TP2={signal['tp2']} ({signal['tp2_possibility']}%), TP3={signal['tp3']} ({signal['tp3_possibility']}%), Trade Type={trade_type}")
        print("✅ Signal SENT ✅")
        return signal
    except Exception as e:
        log(f"Error with {symbol}: {e}", level='ERROR')
        return None

async def scan_symbols():
    exchange = await initialize_binance()
    if not exchange:
        log("Failed to initialize exchange, exiting")
        return

    symbols = await load_symbols(exchange)
    if not symbols:
        log("No symbols loaded, exiting")
        await exchange.close()
        return

    sent_signals = load_sent_signals()
    BATCH_SIZE = 5

    while True:
        current_date = datetime.utcnow().date().isoformat()
        sent_signals = {k: v for k, v in sent_signals.items() if v["date"] == current_date}
        save_sent_signals(sent_signals)

        memory = psutil.Process().memory_info().rss / 1024 / 1024
        log(f"Memory usage: {memory:.2f} MB")
        log(f"Processing {len(symbols)} USDT symbols")

        processed_symbols = set()
        ticker_cache = {}
        ohlcv_cache = {}
        for i in range(0, len(symbols), BATCH_SIZE):
            batch = symbols[i:i + BATCH_SIZE]
            log(f"Processing batch {i//BATCH_SIZE + 1} with {len(batch)} symbols")
            tasks = [
                process_symbol(symbol, exchange, sent_signals, current_date, processed_symbols, ticker_cache, ohlcv_cache)
            for symbol in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for symbol, result in zip(batch, results):
                if result and isinstance(result, dict):
                    sent_signals[symbol] = {
                        "date": current_date,
                        "timestamp": time.time(),
                        "direction": result["prediction"],
                        "trade_type": result["trade_type"]
                    }
                    save_sent_signals(sent_signals)
                processed_symbols.add(symbol)

            memory = psutil.Process().memory_info().rss / 1024 / 1024
            log(f"Batch {i//BATCH_SIZE + 1} completed, memory usage: {memory:.2f} MB")
            ticker_cache.clear()
            ohlcv_cache.clear()

        log(f"Processed {len(processed_symbols)} symbols")
        await update_signal_status()

        # Schedule daily report at 23:59
        now = datetime.utcnow()
        next_report = datetime(now.year, now.month, now.day, 23, 59)
        if now > next_report:
            next_report += timedelta(days=1)
        wait_seconds = (next_report - now).total_seconds()
        if wait_seconds <= 240:
            await generate_daily_summary()
            log("Daily report generated and sent")
            await asyncio.sleep(240)
            continue

        await exchange.close()
        exchange = await initialize_binance()
        await asyncio.sleep(240)

@app.on_event("startup")
async def start_background_loop():
    asyncio.create_task(scan_symbols())

if __name__ == "__main__":
    log("Starting CryptoSniper application")
    uvicorn.run(app, host="0.0.0.0", port=8000)
