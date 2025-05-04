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

CONFIDENCE_THRESHOLD = 65
MIN_VOLUME = 5000  # Keep volume filter for accurate signals
BLACKLISTED_PAIRS = [
    '1000PEPE/USDT', '1000FLOKI/USDT', '1000SATS/USDT',
    '1000BONK/USDT', '1000RATS/USDT', 'TRUMP/USDT',
    'MELANIA/USDT', 'ANIME/USDT', 'PIPPIN/USDT'
]

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
    # Initialize Binance exchange with API credentials
    try:
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        if not api_key or not api_secret:
            log("Binance API key or secret missing", level='ERROR')
            return None
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'},
            'apiKey': api_key,
            'secret': api_secret
        })
        # Test API connectivity with retries
        for attempt in range(3):
            try:
                await exchange.fetch_balance()
                log("Binance API credentials validated")
                break
            except Exception as e:
                log(f"Attempt {attempt + 1} failed to validate API credentials: {e}", level='ERROR')
                if attempt == 2:
                    log("Failed to validate Binance API credentials after retries", level='ERROR')
                    return None
                await asyncio.sleep(2)
        await exchange.load_markets()
        log("Binance exchange initialized")
        return exchange
    except Exception as e:
        log(f"Failed to initialize Binance exchange: {e}", level='ERROR')
        return None

async def load_symbols(exchange):
    # Load valid USDT perpetual futures symbols
    try:
        # Fetch markets with retries
        markets = None
        for attempt in range(3):
            try:
                markets = await exchange.fetch_markets()
                if markets:
                    break
                log(f"Attempt {attempt + 1}: No markets received from Binance API", level='WARNING')
            except Exception as e:
                log(f"Attempt {attempt + 1} failed to fetch markets: {e}", level='ERROR')
            if attempt < 2:
                await asyncio.sleep(2)
        if not markets:
            log("Failed to fetch markets after retries", level='ERROR')
            return []

        symbols = []
        for market in markets:
            symbol = market.get('symbol', '')
            if not symbol:
                log("Market missing symbol", level='DEBUG')
                continue
            quote = market.get('quote', '')
            active = market.get('active', False)
            market_type = market.get('type', '')
            contract_type = market.get('info', {}).get('contractType', '')
            quote_volume = float(market['info'].get('quoteVolume', 0))
            
            is_valid = (
                quote == 'USDT' and
                active and
                market_type == 'future' and
                contract_type == 'PERPETUAL' and
                symbol not in BLACKLISTED_PAIRS and
                quote_volume >= MIN_VOLUME
            )
            if is_valid:
                symbols.append(symbol)
            else:
                log(f"Filtered out {symbol}: quote={quote}, active={active}, type={market_type}, contractType={contract_type}, volume={quote_volume}", level='DEBUG')
        log(f"Loaded {len(symbols)} valid USDT symbols: {symbols}")
        return symbols
    except Exception as e:
        log(f"Failed to load markets: {e}", level='ERROR')
        return []

def load_sent_signals():
    # Load previously sent signals from JSON file
    try:
        with open("logs/sent_signals.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        log(f"Error loading sent_signals: {e}", level='ERROR')
        return {}

def save_sent_signals(sent_signals):
    # Save sent signals to JSON file
    try:
        with open("logs/sent_signals.json", "w") as f:
            json.dump(sent_signals, f)
    except Exception as e:
        log(f"Error saving sent_signals: {e}", level='ERROR')

async def get_last_direction(symbol, exchange):
    # Check the last signal direction for a symbol
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

        if direction == "LONG":
            if (
                current_price >= tp1 or 
                current_price >= tp2 or 
                current_price >= tp3 or 
                current_price <= sl or 
                time_elapsed >= 5 * 3600
            ):
                return None
        elif direction == "SHORT":
            if (
                current_price <= tp1 or 
                current_price <= tp2 or 
                current_price <= tp3 or 
                current_price >= sl or 
                time_elapsed >= 5 * 3600
            ):
                return None
        return direction, tp1, tp2, entry_price
    except Exception as e:
        log(f"Error checking last direction for {symbol}: {e}", level='ERROR')
        return None

async def fetch_clean_ohlcv(exchange, symbol, timeframe, limit):
    # Fetch and clean OHLCV data for a symbol
    try:
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df = df.replace([np.inf, -np.inf], np.nan).dropna()
        df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].replace(0, np.nan).fillna(method='ffill')
        if df.empty:
            log(f"No valid data for {symbol}", level='WARNING')
        return df
    except Exception as e:
        log(f"Error fetching OHLCV for {symbol}: {e}", level='ERROR')
        return pd.DataFrame()

async def process_symbol(symbol, exchange, sent_signals, current_date, processed_symbols, ticker_cache, ohlcv_cache):
    # Process a symbol to generate trading signals
    try:
        if symbol in processed_symbols or symbol in BLACKLISTED_PAIRS:
            return None

        if symbol in sent_signals and sent_signals[symbol]["date"] == current_date:
            return None

        await asyncio.sleep(1.2)
        if symbol not in exchange.markets:
            log(f"{symbol} not found in markets", level='WARNING')
            return None

        if symbol in ticker_cache:
            ticker = ticker_cache[symbol]
        else:
            ticker = await exchange.fetch_ticker(symbol)
            ticker_cache[symbol] = ticker

        if not ticker or ticker.get("baseVolume", 0) < MIN_VOLUME:
            log(f"Low volume for {symbol}: {ticker.get('baseVolume', 0)}", level='WARNING')
            return None

        timeframe = "15m"
        trade_type = "Scalp"
        if ticker.get("baseVolume", 0) < 25000:
            timeframe = "1h"
            trade_type = "Normal"

        if symbol in ohlcv_cache:
            ohlcv = ohlcv_cache[symbol]
        else:
            ohlcv = await fetch_clean_ohlcv(exchange, symbol, timeframe, limit=50)
            ohlcv_cache[symbol] = ohlcv

        if ohlcv.empty:
            return None

        result = await analyze_symbol(exchange, symbol)
        if not result or not result.get("signal"):
            log(f"No signal generated for {symbol}", level='WARNING')
            return None

        signal = result
        signal["prediction"] = await predict_trend(symbol, exchange)
        if signal["prediction"] not in ["LONG", "SHORT"]:
            signal["prediction"] = signal["signal"]

        last_info = await get_last_direction(symbol, exchange)
        if last_info:
            last_dir, tp1, tp2, entry_price = last_info
            if last_dir == signal["prediction"]:
                return None
            ticker = await exchange.fetch_ticker(symbol)
            current_price = ticker["last"]
            if last_dir == "LONG" and signal["prediction"] == "SHORT":
                if current_price < tp1 and current_price < tp2:
                    return None
            elif last_dir == "SHORT" and signal["prediction"] == "LONG":
                if current_price > tp1 and current_price > tp2:
                    return None

        confidence = min(signal.get("confidence", 0), 100)
        tp1_possibility = signal.get("tp1_chance", 0)
        log(f"🔍 {symbol} | Confidence: {confidence:.2f} | Direction: {signal['prediction']} | TP1 Chance: {tp1_possibility:.2f} | Trade Type: {trade_type}")

        if confidence < CONFIDENCE_THRESHOLD:
            log(f"Low confidence for {symbol}: {confidence}", level='WARNING')
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
        return signal
    except Exception as e:
        log(f"Error with {symbol}: {e}", level='ERROR')
        return None

async def scan_symbols():
    # Main loop to scan symbols and generate signals
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
    BATCH_SIZE = 3

    while True:
        try:
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
                    for symbol in batch if symbol not in BLACKLISTED_PAIRS
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

        except Exception as e:
            log(f"Scan loop error: {e}", level='ERROR')
        finally:
            await exchange.close()
            exchange = await initialize_binance()
            await asyncio.sleep(240)

@app.on_event("startup")
async def start_background_loop():
    asyncio.create_task(scan_symbols())

if __name__ == "__main__":
    log("Starting CryptoSniper application")
    uvicorn.run(app, host="0.0.0.0", port=8000)
