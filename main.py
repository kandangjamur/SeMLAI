# main.py
import os, time, json, sys, asyncio
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
import psutil
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from core.analysis import multi_timeframe_analysis
from core.engine import predict_trend
from utils.logger import log, log_signal_to_csv
from telebot.bot import send_signal
from data.tracker import update_signal_status

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
                        "tp1_possibility": float(parts[10]) if parts[10] else 0,
                        "tp2_possibility": float(parts[11]) if len(parts) > 11 and parts[11] else 0,
                        "tp3_possibility": float(parts[12]) if len(parts) > 12 and parts[12] else 0
                    })
    except:
        log("No signals found.")
    return templates.TemplateResponse("dashboard.html", {"request": request, "signals": signals})

async def initialize_binance():
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'},
        'apiKey': os.getenv("BINANCE_API_KEY"),
        'secret': os.getenv("BINANCE_API_SECRET")
    })
    await exchange.load_markets()
    log("Binance exchange initialized")
    return exchange

async def load_symbols(exchange):
    blacklist = ['TUSD/USDT', 'USDC/USDT', 'BUSD/USDT', 'LUNA/USDT', 'WING/USDT']
    symbols = [
        s['symbol'] for s in exchange.markets.values()
        if s['quote'] == 'USDT' and s['active']
        and not any(x in s['symbol'] for x in ["UP/USDT", "DOWN/USDT", "BULL", "BEAR", "3S", "3L"])
        and s['symbol'] not in blacklist and s['symbol'] in exchange.symbols
    ]
    log(f"Loaded {len(symbols)} valid USDT symbols")
    return symbols

def load_sent_signals():
    try:
        with open("logs/sent_signals.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_sent_signals(data):
    with open("logs/sent_signals.json", "w") as f:
        json.dump(data, f)

async def process_symbol(symbol, exchange, sent, today):
    try:
        await asyncio.sleep(0.4)
        ticker = await exchange.fetch_ticker(symbol)
        if ticker.get("baseVolume", 0) < 100000:
            return

        result = await multi_timeframe_analysis(symbol, exchange)
        if not result: return

        result["prediction"] = await predict_trend(symbol, exchange)
        if result["prediction"] not in ["LONG", "SHORT"]:
            return

        if symbol in sent and sent[symbol]["date"] == today:
            if sent[symbol]["direction"] == result["prediction"]:
                return

        confidence = result.get("confidence", 0)
        if confidence < 50: return

        result["direction"] = result["prediction"]
        result["leverage"] = 10
        atr = result.get("atr", 0.01)
        price = result["price"]
        result["tp1_possibility"] = round(min(95, confidence + 5 if atr / price < 0.02 else confidence), 1)
        result["tp2_possibility"] = round(min(85, confidence - 5), 1)
        result["tp3_possibility"] = round(min(75, confidence - 10), 1)

        await send_signal(symbol, result)
        log_signal_to_csv(result)
        sent[symbol] = {"date": today, "direction": result["prediction"], "timestamp": time.time()}
        save_sent_signals(sent)
        log(f"Signal sent: {symbol} {result['direction']} conf={confidence}")
    except Exception as e:
        log(f"Error with {symbol}: {e}")

async def main_loop():
    exchange = await initialize_binance()
    symbols = await load_symbols(exchange)
    CONFIDENCE_THRESHOLD = 50
    sent_signals = load_sent_signals()

    while True:
        today = datetime.utcnow().date().isoformat()
        sent_signals = {k: v for k, v in sent_signals.items() if v["date"] == today}
        save_sent_signals(sent_signals)

        mem = psutil.Process().memory_info().rss / 1024 / 1024
        log(f"🛠️ Memory: {mem:.2f} MB")
        log("🔁 New Scan Cycle Started")

        tasks = [process_symbol(s, exchange, sent_signals, today) for s in symbols]
        await asyncio.gather(*tasks)

        await update_signal_status()
        await exchange.close()
        exchange = await initialize_binance()
        await asyncio.sleep(240)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(main_loop())
