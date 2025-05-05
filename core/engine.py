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

async def run_engine():
    log("Starting engine...")
    try:
        # Initialize Telegram bot
        log("Initializing Telegram bot...")
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        try:
            await bot.get_me()
            log("Telegram bot initialized successfully")
        except Exception as e:
            log(f"Failed to initialize Telegram bot: {e}", level='ERROR')
            return

        # Initialize exchange
        log("Initializing Binance exchange...")
        exchange = ccxt.binance({"enableRateLimit": True})
        try:
            markets = await exchange.load_markets()
            symbols = [s for s in markets.keys() if s.endswith("/USDT")]
            log(f"Loaded {len(symbols)} USDT pairs for scanning")
        except Exception as e:
            log(f"Failed to load markets: {e}", level='ERROR')
            return

        for symbol in symbols:
            memory_before = psutil.Process().memory_info().rss / 1024 / 1024
            cpu_percent = psutil.cpu_percent(interval=0.1)
            log(f"[{symbol}] Before analysis - Memory: {memory_before:.2f} MB, CPU: {cpu_percent:.1f}%")

            log(f"Analyzing {symbol}...")
            try:
                ohlcv = await exchange.fetch_ohlcv(symbol, "1h", limit=100)
                df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"], dtype="float32")
            except Exception as e:
                log(f"[{symbol}] Error fetching OHLCV: {e}", level='ERROR')
                continue

            if not detect_whale_activity(symbol, df):
                log(f"[{symbol}] No whale activity detected", level='INFO')
                continue

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
                    try:
                        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
                        log(f"[{symbol}] Signal sent: {signal['direction']}, Confidence: {signal['confidence']}%")
                    except Exception as e:
                        log(f"[{symbol}] Error sending Telegram message: {e}", level='ERROR')

                    signal_df = pd.DataFrame([signal])
                    signal_df.to_csv("logs/signals_log.csv", mode="a", header=not os.path.exists("logs/signals_log.csv"), index=False)
                else:
                    log(f"⚠️ {symbol} - No valid signal", level='INFO')
            except Exception as e:
                log(f"[{symbol}] Error analyzing symbol: {e}", level='ERROR')
                continue

            memory_after = psutil.Process().memory_info().rss / 1024 / 1024
            cpu_percent_after = psutil.cpu_percent(interval=0.1)
            memory_diff = memory_after - memory_before
            log(f"[{symbol}] After analysis - Memory: {memory_after:.2f} MB (Change: {memory_diff:.2f} MB), CPU: {cpu_percent_after:.1f}%")
    except Exception as e:
        log(f"Critical error in engine: {e}", level='ERROR')
    finally:
        try:
            await exchange.close()
            log("Exchange connection closed")
        except Exception as e:
            log(f"Error closing exchange: {e}", level='ERROR')
