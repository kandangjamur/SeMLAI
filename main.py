import asyncio
import ccxt.async_support as ccxt
from fastapi import FastAPI
import pandas as pd
import numpy as np
from model.predictor import SignalPredictor
from utils.support_resistance import find_support_resistance, detect_breakout
from utils.logger import log
from core.analysis import analyze_symbol
import httpx
import os
import logging
import warnings
import gc
from datetime import datetime
import pytz

app = FastAPI()

predictor = None
binance = None
symbols = []
MINIMUM_DAILY_VOLUME = 1000000
SYMBOL_LIMIT = 150

async def initialize():
    global predictor, binance, symbols
    try:
        predictor = SignalPredictor()
        binance = ccxt.binance({
            'apiKey': os.getenv('BINANCE_API_KEY'),
            'secret': os.getenv('BINANCE_API_SECRET'),
            'enableRateLimit': True,
        })
        await binance.load_markets()
        log("Binance API connection successful.", level="INFO")
        
        markets = await binance.fetch_markets()
        usdt_pairs = [market['symbol'] for market in markets if market['quote'] == 'USDT']
        
        ticker_data = await asyncio.gather(*[binance.fetch_ticker(symbol) for symbol in usdt_pairs], return_exceptions=True)
        symbols = []
        for ticker in ticker_data:
            if isinstance(ticker, Exception):
                log(f"Error fetching ticker for a symbol: {str(ticker)}", level="WARNING")
                continue
            if ticker.get('quoteVolume') is not None and ticker.get('close') is not None:
                if ticker['quoteVolume'] * ticker['close'] >= MINIMUM_DAILY_VOLUME:
                    symbols.append(ticker['symbol'])
        
        symbols = symbols[:SYMBOL_LIMIT]
        log(f"Selected {len(symbols)} USDT pairs with volume >= ${MINIMUM_DAILY_VOLUME}", level="INFO")
        log(f"Scanning {len(symbols)} symbols (limited to {SYMBOL_LIMIT})", level="INFO")
    except Exception as e:
        log(f"Error during initialization: {str(e)}", level="ERROR")
        raise
    finally:
        gc.collect()

async def send_telegram_message(signal):
    try:
        async with httpx.AsyncClient() as client:
            message = (
                f"⚡ Trade Pair: {signal['symbol']}\n"
                f"📉 Trade Type: Normal\n"
                f"🎯 Direction: {signal['direction']}\n"
                f"🚀 Entry: {signal['entry']:.4f}\n"
                f"🎯 TP1: {signal['tp1']:.4f} ({signal['tp1_possibility']*100:.1f}%)\n"
                f"💰 TP2: {signal['tp2']:.4f} ({signal['tp2_possibility']*100:.1f}%)\n"
                f"📈 TP3: {signal['tp3']:.4f} ({signal['tp3_possibility']*100:.1f}%)\n"
                f"🛡️ SL: {signal['sl']:.4f}\n"
                f"📊 Confidence: {signal['confidence']:.2f}%\n"
                f"⏰ Time: {signal['timestamp']}"
            )
            payload = {
                "chat_id": os.getenv("TELEGRAM_CHAT_ID"),
                "text": message,
                "parse_mode": "Markdown"
            }
            response = await client.post(
                f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage",
                json=payload
            )
            response.raise_for_status()
            log("Telegram message sent successfully.", level="INFO")
    except Exception as e:
        log(f"Error sending Telegram message: {str(e)}", level="ERROR")

async def log_signal(signal):
    try:
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, "signals_log_new.csv")
        signal_df = pd.DataFrame([signal])
        signal_df.to_csv(log_file, mode='a', header=not os.path.exists(log_file), index=False)
        log(f"Signal logged to {log_file}", level="INFO")
    except Exception as e:
        log(f"Error logging signal: {str(e)}", level="ERROR")

async def trading_loop():
    while True:
        try:
            for symbol in symbols:
                try:
                    signal = await analyze_symbol(symbol, binance, predictor)
                    if signal:
                        log(f"🔍 {signal['symbol']} | Confidence: {signal['confidence']:.2f} | Direction: {signal['direction']} | TP1 Chance: {signal['tp1_possibility']:.2f}", level="INFO")
                        signal['timestamp'] = pd.Timestamp.now(tz=pytz.timezone("Asia/Karachi")).isoformat()
                        await send_telegram_message(signal)
                        await log_signal(signal)
                        log("✅ Signal SENT ✅", level="INFO")
                        log("---", level="INFO")
                    else:
                        log(f"⚠️ {symbol} - No valid signal", level="INFO")
                except Exception as e:
                    log(f"Error analyzing {symbol}: {str(e)}", level="ERROR")
                finally:
                    gc.collect()
            await asyncio.sleep(60)
        except Exception as e:
            log(f"Error in trading loop: {str(e)}", level="ERROR")
            await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    await initialize()
    asyncio.create_task(trading_loop())

@app.get("/health")
async def health_check():
    if predictor is not None and binance is not None and symbols:
        return {"status": "healthy"}
    return {"status": "unhealthy"}, 503

@app.on_event("shutdown")
async def shutdown_event():
    log("Shutting down", level="INFO")
    if binance:
        try:
            await binance.close()
            log("Binance connection closed successfully.", level="INFO")
        except Exception as e:
            log(f"Error closing Binance connection: {str(e)}", level="ERROR")
    log("Application shutdown complete.", level="INFO")
