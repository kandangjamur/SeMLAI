# main.py
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
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import logging
import sys
import asyncio
from datetime import datetime
import psutil
import pandas as pd

logging.basicConfig(filename="logs/crash.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
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
    except Exception as e:
        log(f"Error reading signals log: {e}")
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
        log(f"Failed to initialize Binance exchange: {e}")
        sys.exit(1)

async def load_symbols(exchange):
    try:
        invalid = {'TUSD/USDT', 'USDC/USDT', 'BUSD/USDT', 'LUNA/USDT', 'WING/USDT', 'FTT/USDT', 'CVC/USDT', 'EUR/USDT', 'WAN/USDT', 'WIN/USDT', 'TFUEL/USDT'}
        symbols = []
        for s in exchange.symbols:
            if "/USDT" in s and s not in invalid and all(x not in s for x in ["UP", "DOWN", "BULL", "BEAR", "3S", "3L", "5S", "5L"]):
                try:
                    market = exchange.market(s)
                    if market.get("active") and market.get("quote") == "USDT":
                        symbols.append(s)
                except:
                    continue
        log(f"Loaded {len(symbols)} valid USDT symbols")
        return symbols[:60]
    except Exception as e:
        log(f"Failed to load symbols: {e}")
        return []

def load_sent_signals():
    try:
        with open("logs/sent_signals.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_sent_signals(data):
    try:
        with open("logs/sent_signals.json", "w") as f:
            json.dump(data, f)
    except Exception as e:
        log(f"Error saving sent_signals: {e}")

async def process_symbol(symbol, exchange, CONFIDENCE_THRESHOLD, sent_signals, today, processed):
    try:
        if symbol in processed or symbol in sent_signals and sent_signals[symbol]["date"] == today:
            return None

        await asyncio.sleep(0.5)
        ticker = await exchange.fetch_ticker(symbol)
        if not ticker or ticker.get("baseVolume") is None or ticker["baseVolume"] < 100000:
            return None

        signal = await multi_timeframe_analysis(symbol, exchange)
        if not signal:
            return None

        signal['prediction'] = await predict_trend(symbol, exchange)
        if signal['prediction'] not in ["LONG", "SHORT"]:
            return None

        confidence = signal.get("confidence", 0)
        if confidence < CONFIDENCE_THRESHOLD:
            return None

        price = signal["price"]
        atr = signal.get("atr", 0.01)
        v = max(0.5, min(2.0, confidence / 50))
        signal["tp1_possibility"] = round(min(95, 100 - (abs(signal["tp1"] - price) / price * 100) * v), 2)
        signal["tp2_possibility"] = round(min(85, 95 - (abs(signal["tp2"] - price) / price * 100) * v * 1.2), 2)
        signal["tp3_possibility"] = round(min(75, 90 - (abs(signal["tp3"] - price) / price * 100) * v * 1.5), 2)

        signal["direction"] = signal["prediction"]
        signal["leverage"] = 10

        await send_signal(symbol, signal)
        log_signal_to_csv(signal)
        sent_signals[symbol] = {
            "date": today,
            "timestamp": time.time(),
            "direction": signal["prediction"]
        }
        save_sent_signals(sent_signals)
        log(f"✅ Signal sent for {symbol}: {signal['prediction']} ({confidence})")
        return signal
    except Exception as e:
        log(f"Error in process_symbol({symbol}): {e}")
        return None

async def main_loop():
    try:
        exchange = await initialize_binance()
        CONFIDENCE_THRESHOLD = 70

        while True:
            symbols = await load_symbols(exchange)
            sent_signals = load_sent_signals()
            today = datetime.utcnow().date().isoformat()
            sent_signals = {k: v for k, v in sent_signals.items() if v["date"] == today}
            save_sent_signals(sent_signals)

            log(f"🛠️ Memory: {psutil.Process().memory_info().rss / 1024 / 1024:.2f} MB")
            log("🔁 New Scan Cycle Started")

            processed = set()
            tasks = [process_symbol(s, exchange, CONFIDENCE_THRESHOLD, sent_signals, today, processed) for s in symbols]
            await asyncio.gather(*tasks, return_exceptions=True)
            await update_signal_status()

            await exchange.close()
            exchange = await initialize_binance()
            await asyncio.sleep(240)
    except Exception as e:
        log(f"Main loop error: {e}")
    finally:
        if 'exchange' in locals():
            await exchange.close()

@app.on_event("startup")
async def start_background():
    asyncio.create_task(main_loop())
