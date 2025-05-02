# main.py
import os, sys, json, time, asyncio, logging
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

logging.basicConfig(filename="logs/crash.log", level=logging.INFO)

app = FastAPI()
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")
templates = Jinja2Templates(directory="dashboard/templates")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    signals = []
    try:
        if os.path.exists("logs/signals_log.csv"):
            df = pd.read_csv("logs/signals_log.csv").tail(50)
            for _, row in df.iterrows():
                signals.append(row.to_dict())
    except Exception as e:
        log(f"Dashboard error: {e}")
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
    invalid = {"UP/USDT", "DOWN/USDT", "BULL", "BEAR", "3S", "3L", "5S", "5L"}
    symbols = [
        s for s in exchange.symbols
        if s.endswith("/USDT") and s not in exchange.markets and not any(x in s for x in invalid)
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
    try:
        with open("logs/sent_signals.json", "w") as f:
            json.dump(data, f)
    except Exception as e:
        log(f"Failed saving signals: {e}")

async def get_last_direction(symbol):
    try:
        if not os.path.exists("logs/signals_log.csv"):
            return None
        df = pd.read_csv("logs/signals_log.csv")
        df = df[df.symbol == symbol]
        if df.empty:
            return None
        row = df.iloc[-1]
        return row.direction, float(row.tp1), float(row.price), float(row.sl), pd.to_datetime(row.timestamp).timestamp()
    except:
        return None

async def process_symbol(symbol, exchange, sent_signals, date, threshold):
    try:
        if symbol not in exchange.symbols:
            return
        if sent_signals.get(symbol, {}).get("date") == date:
            return

        ticker = await exchange.fetch_ticker(symbol)
        if ticker["baseVolume"] < 100000:
            return

        result = await multi_timeframe_analysis(symbol, exchange)
        if not result:
            return

        result["prediction"] = await predict_trend(symbol, exchange) or "LONG"
        direction, tp1, price, sl, ts = await get_last_direction(symbol) or (None, None, None, None, None)
        if direction and result["prediction"] != direction and time.time() - ts < 18000:
            return

        conf = result.get("confidence", 0)
        if conf < threshold:
            return

        atr = result.get("atr", 0.01)
        volatility = atr / result["price"]
        result.update({
            "tp1_possibility": round(min(95, conf + 5 if volatility < 0.02 else conf), 1),
            "tp2_possibility": round(min(85, conf - 5 if volatility < 0.02 else conf - 10), 1),
            "tp3_possibility": round(min(75, conf - 15 if volatility < 0.02 else conf - 20), 1)
        })

        await send_signal(symbol, result)
        log_signal_to_csv(result)
        sent_signals[symbol] = {"date": date, "timestamp": time.time(), "direction": result["prediction"]}
        save_sent_signals(sent_signals)
        log(f"Signal sent: {symbol} {result['prediction']} (TP1: {result['tp1_possibility']}%)")
    except Exception as e:
        log(f"Error with {symbol}: {e}")

async def main_loop():
    try:
        threshold = 50
        exchange = await initialize_binance()
        while True:
            symbols = await load_symbols(exchange)
            if not symbols:
                break

            sent_signals = load_sent_signals()
            current_date = datetime.utcnow().date().isoformat()
            sent_signals = {k: v for k, v in sent_signals.items() if v["date"] == current_date}
            save_sent_signals(sent_signals)

            log(f"🛠️ Memory: {psutil.Process().memory_info().rss / 1024 / 1024:.2f} MB")
            log("🔁 New Scan Cycle Started")

            tasks = [
                process_symbol(s, exchange, sent_signals, current_date, threshold)
                for s in symbols
            ]
            await asyncio.gather(*tasks)
            await update_signal_status()
            await exchange.close()
            exchange = await initialize_binance()
            await asyncio.sleep(240)
    except Exception as e:
        log(f"Main loop error: {e}")
        sys.exit(1)

@app.on_event("startup")
async def start_loop():
    asyncio.create_task(main_loop())
