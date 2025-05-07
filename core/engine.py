import asyncio
import ccxt.async_support as ccxt
from core.analysis import analyze_symbol
from core.whale_detector import detect_whale_activity
from utils.logger import log
import pandas as pd
import psutil
from telegram import Bot
import os
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

async def run_engine():
    log("[Engine] Starting run_engine")

    try:
        log("[Engine] Checking environment variables")
        if not all([BINANCE_API_KEY, BINANCE_API_SECRET, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
            log("[Engine] Missing environment variables", level='ERROR')
            return

        log("[Engine] Checking model file")
        model_path = "models/rf_model.joblib"
        if not os.path.exists(model_path):
            log(f"[Engine] Model file not found at {model_path}", level='ERROR')
            return

        log("[Engine] Initializing Telegram bot")
        try:
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            log("[Engine] Telegram bot initialized")
        except Exception as e:
            log(f"[Engine] Error initializing Telegram bot: {str(e)}", level='ERROR')
            return

        log("[Engine] Initializing Binance exchange")
        try:
            exchange = ccxt.binance({
                "enableRateLimit": True,
                "apiKey": BINANCE_API_KEY,
                "secret": BINANCE_API_SECRET
            })
            log("[Engine] Binance exchange initialized")
        except Exception as e:
            log(f"[Engine] Error initializing Binance exchange: {str(e)}", level='ERROR')
            return

        log("[Engine] Loading markets")
        try:
            markets = await exchange.load_markets()
            symbols = [s for s in markets.keys() if s.endswith("/USDT")]
            log(f"[Engine] Found {len(symbols)} USDT pairs")
        except Exception as e:
            log(f"[Engine] Error loading markets: {str(e)}", level='ERROR')
            return

        for symbol in symbols:
            memory_before = psutil.Process().memory_info().rss / 1024 / 1024
            cpu_percent = psutil.cpu_percent(interval=0.1)
            log(f"[Engine] [{symbol}] Before analysis - Memory: {memory_before:.2f} MB, CPU: {cpu_percent:.1f}%")

            log(f"[Engine] [{symbol}] Checking whale activity")
            try:
                ohlcv = await exchange.fetch_ohlcv(symbol, "1h", limit=100)
                df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"], dtype="float32")
                log(f"[Engine] [{symbol}] OHLCV fetched")
            except Exception as e:
                log(f"[Engine] [{symbol}] Error fetching OHLCV: {str(e)}", level='ERROR')
                continue

            if not detect_whale_activity(symbol, df):
                log(f"[Engine] [{symbol}] No whale activity detected")
                continue

            log(f"[Engine] [{symbol}] Analyzing symbol")
            try:
                signal = await analyze_symbol(exchange, symbol)
                if signal and signal["confidence"] >= 80 and signal["tp1_chance"] >= 75:
                    message = (
                        f"🚨 {signal['symbol']} Signal\n"
                        f"Timeframe: {signal['timeframe']}\n"
                        f"Direction: {signal['direction']}\n"
                        f"Price: {signal['price']:.4f}\n"
                        f"Confidence: {signal['confidence']}%\n"
                        f"TP1: {signal['tp1']:.4f} ({signal['tp1_chance']}%)\n"
                        f"TP2: {signal['tp2']:.4f}\n"
                        f"TP3: {signal['tp3']:.4f}\n"
                        f"SL: {signal['sl']:.4f}"
                    )
                    log(f"[Engine] [{symbol}] Signal generated, sending to Telegram")
                    try:
                        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
                        log(f"[Engine] [{symbol}] Signal sent: {signal['direction']}, Confidence: {signal['confidence']}%")
                    except Exception as e:
                        log(f"[Engine] [{symbol}] Error sending Telegram message: {str(e)}", level='ERROR')

                    signal_df = pd.DataFrame([signal])
                    log(f"[Engine] [{symbol}] Saving signal to CSV")
                    signal_df.to_csv("logs/signals_log.csv", mode="a", header=not os.path.exists("logs/signals_log.csv"), index=False)
                    log(f"[Engine] [{symbol}] Signal saved to CSV")
                else:
                    log(f"[Engine] [{symbol}] No valid signal")
            except Exception as e:
                log(f"[Engine] [{symbol}] Error analyzing symbol: {str(e)}", level='ERROR')
                continue

            memory_after = psutil.Process().memory_info().rss / 1024 / 1024
            cpu_percent_after = psutil.cpu_percent(interval=0.1)
            memory_diff = memory_after - memory_before
            log(f"[Engine] [{symbol}] After analysis - Memory: {memory_after:.2f} MB (Change: {memory_diff:.2f} MB), CPU: {cpu_percent_after:.1f}%")

        log("[Engine] Closing exchange")
        try:
            await exchange.close()
            log("[Engine] Exchange closed")
        except Exception as e:
            log(f"[Engine] Error closing exchange: {str(e)}", level='ERROR')

    except Exception as e:
        log(f"[Engine] Unexpected error in run_engine: {str(e)}", level='ERROR')
