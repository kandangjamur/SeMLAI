import asyncio
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from core.analysis import analyze_symbol
from telebot.sender import send_telegram_signal
from utils.logger import log, log_signal_to_csv
import ccxt.async_support as ccxt
import os
import psutil
from dotenv import load_dotenv
from time import time
import cachetools

# FastAPI app
app = FastAPI()

# Thresholds
CONFIDENCE_THRESHOLD = 80
TP1_POSSIBILITY_THRESHOLD = 75
SCALPING_CONFIDENCE_THRESHOLD = 85

# Cache for API calls
symbol_cache = cachetools.TTLCache(maxsize=100, ttl=300)  # 5-minute cache

# Health check endpoints
@app.get("/")
async def root():
    log("Root endpoint accessed")
    return {"message": "Crypto Signal Bot is running."}

@app.get("/health")
async def health():
    log("Health check endpoint accessed")
    return {"status": "healthy", "message": "Bot is operational."}

def log_memory_usage():
    process = psutil.Process()
    mem_info = process.memory_info()
    mem_mb = mem_info.rss / (1024 * 1024)
    log(f"Memory usage: {mem_mb:.2f} MB")
    return mem_mb

async def get_valid_symbols(exchange):
    if "valid_symbols" in symbol_cache:
        log("Using cached symbols")
        return symbol_cache["valid_symbols"]
    
    log("Fetching USDT symbols...")
    try:
        markets = await exchange.load_markets()
        usdt_symbols = [s for s in markets.keys() if s.endswith('/USDT') and markets[s].get('active', False)]
        symbol_cache["valid_symbols"] = usdt_symbols
        log(f"Found {len(usdt_symbols)} active USDT pairs")
        return usdt_symbols
    except Exception as e:
        log(f"Error fetching symbols: {e}", level='ERROR')
        return []
    finally:
        await exchange.close()

async def scan_symbols():
    log("Starting symbol scan...")
    exchange = ccxt.binance({
        'apiKey': os.getenv("BINANCE_API_KEY"),
        'secret': os.getenv("BINANCE_API_SECRET"),
        'enableRateLimit': True,
    })

    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    if not api_key or not api_secret:
        log("API Key or Secret is missing! Check Koyeb Config Vars.", level='ERROR')
        return

    try:
        log("Testing Binance API connection...")
        ticker = await exchange.fetch_ticker('BTC/USDT')
        log(f"Binance API connection successful. BTC/USDT ticker: {ticker['last']}")

        symbols = await get_valid_symbols(exchange)
        if not symbols:
            log("No valid USDT symbols found!", level='ERROR')
            return

        log(f"Scanning {len(symbols)} symbols...")
        for symbol in symbols[:50]:  # Limit to 50 symbols to save memory
            try:
                log_memory_usage()
                log(f"Analyzing {symbol}...")
                result = await analyze_symbol(exchange, symbol)
                if not result or not result.get('signal'):
                    log(f"⚠️ {symbol} - No valid signal")
                    continue

                confidence = result.get("confidence", 0)
                tp1_possibility = result.get("tp1_chance", 0)
                direction = result.get("signal", "none")
                price = result.get("price", 0)
                tp1 = result.get("tp1", 0)
                tp2 = result.get("tp2", 0)
                tp3 = result.get("tp3", 0)
                sl = result.get("sl", 0)
                leverage = result.get("leverage", 10)
                trade_type = result.get("trade_type", "Scalping")

                log(
                    f"🔍 {symbol} | Confidence: {confidence:.2f} | "
                    f"Direction: {direction} | TP1 Chance: {tp1_possibility:.2f} | "
                    f"Entry: {price:.4f} | TP1: {tp1:.4f} | TP2: {tp2:.4f} | "
                    f"TP3: {tp3:.4f} | SL: {sl:.4f} | Leverage: {leverage}x"
                )

                signal_data = {
                    "symbol": symbol,
                    "direction": direction,
                    "confidence": confidence,
                    "price": price,
                    "tp1": tp1,
                    "tp2": tp2,
                    "tp3": tp3,
                    "sl": sl,
                    "tp1_possibility": tp1_possibility,
                    "leverage": leverage,
                    "trade_type": trade_type,
                    "timestamp": int(time() * 1000),
                    "tp2_possibility": result.get("tp2_possibility", 0),
                    "tp3_possibility": result.get("tp3_possibility", 0),
                    "indicators_used": result.get("indicators_used", ""),
                    "backtest_result": result.get("backtest_result", 0),
                    "volume": result.get("volume", 0)
                }

                if confidence >= CONFIDENCE_THRESHOLD and tp1_possibility >= TP1_POSSIBILITY_THRESHOLD:
                    log(f"Sending Telegram signal for {symbol}...")
                    await send_telegram_signal(symbol, signal_data)
                    log_signal_to_csv(signal_data)
                    log("✅ Signal SENT ✅")
                else:
                    log(f"⚠️ {symbol} - Skipped: Low confidence or TP1 possibility")

                log("---")
                await asyncio.sleep(0.5)  # Prevent overloading Koyeb

            except Exception as e:
                log(f"Error processing {symbol}: {e}", level='ERROR')

    except Exception as e:
        log(f"Error in scan_symbols: {e}", level='ERROR')
    finally:
        await exchange.close()

async def run_bot():
    log("Starting bot...")
    while True:
        try:
            mem_usage = log_memory_usage()
            if mem_usage > 200:  # Stricter memory limit for Koyeb
                log("Memory usage exceeds 200 MB, optimizing...", level='ERROR')
                import gc
                gc.collect()
            log("Initiating scan_symbols...")
            await scan_symbols()
        except Exception as e:
            log(f"Error in run_bot: {e}", level='ERROR')
        log("Waiting 60 seconds before next scan...")
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    log("Main application starting...")
    if not os.getenv("BINANCE_API_KEY") or not os.getenv("BINANCE_API_SECRET"):
        log("BINANCE_API_KEY or BINANCE_API_SECRET not set in environment!", level='ERROR')
        raise Exception("Missing API keys")

    bot_task = asyncio.create_task(run_bot())
    log("Bot task started")

    try:
        yield
    finally:
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            log("Bot task cancelled")

app = FastAPI(lifespan=lifespan)

if __name__ == "__main__":
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    except Exception as e:
        log(f"Error in main application: {e}", level='ERROR')
        exit(1)
