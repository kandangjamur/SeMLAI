import asyncio
import uvicorn
from fastapi import FastAPI
from core.analysis import analyze_symbol
import ccxt.async_support as ccxt
import os
import logging
import pandas as pd
from dotenv import load_dotenv
import telegram
from utils.support_resistance import find_support_resistance
from utils.logger import log
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("scanner")

# Load environment variables
load_dotenv()

# FastAPI app
app = FastAPI()

# Signal thresholds
CONFIDENCE_THRESHOLD = 70  # 70% for high confidence signals
TP1_POSSIBILITY_THRESHOLD = 0.70  # 70% for accurate signals
SCALPING_CONFIDENCE_THRESHOLD = 85  # Below this is Scalping Trade
BACKTEST_FILE = "logs/signals_log.csv"
MIN_VOLUME_USD = 500000  # Minimum 24h volume in USD
COOLDOWN_MINUTES = 30  # Cooldown period for same symbol signals
SCAN_INTERVAL_SECONDS = 1800  # Scan every 30 minutes

# Track last signal time for each symbol
last_signal_time = {}

# Send Telegram message
async def send_telegram_message(message):
    try:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not bot_token or not chat_id:
            logger.error("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing!")
            return
        bot = telegram.Bot(token=bot_token)
        await bot.send_message(chat_id=chat_id, text=message)
        logger.info("Telegram message sent successfully.")
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")

# Log signal to CSV
def log_signal_to_csv(signal, trade_type, atr, leverage, support, resistance, midpoint, prediction):
    try:
        signal_data = {
            "symbol": signal["symbol"],
            "price": signal["entry"],
            "confidence": signal["confidence"],
            "trade_type": trade_type,
            "timestamp": pd.Timestamp.now(tz=ZoneInfo("Asia/Karachi")).isoformat(),
            "tp1": signal["tp1"],
            "tp2": signal["tp2"],
            "tp3": signal["tp3"],
            "sl": signal["sl"],
            "atr": atr,
            "leverage": leverage,
            "support": support,
            "resistance": resistance,
            "midpoint": (support + resistance) / 2 if support and resistance else 0.0,
            "prediction": signal["direction"],
            "tp1_possibility": signal["tp1_possibility"],
            "tp2_possibility": signal["tp2_possibility"],
            "tp3_possibility": signal["tp3_possibility"],
            "status": "open"  # Default status
        }
        df = pd.DataFrame([signal_data])
        # Append to file
        if not os.path.exists(BACKTEST_FILE):
            df.to_csv(BACKTEST_FILE, index=False)
        else:
            df.to_csv(BACKTEST_FILE, mode='a', header=False, index=False)
        logger.info(f"Signal logged to {BACKTEST_FILE}")
    except Exception as e:
        logger.error(f"Error logging signal to CSV: {e}")

# Health check route
@app.get("/")
async def root():
    return {"message": "Crypto Signal Bot is running."}

# Health check for Koyeb
@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Bot is operational."}

# Get USDT pairs with sufficient volume
async def get_valid_symbols(exchange):
    try:
        markets = await exchange.load_markets()
        usdt_symbols = [s for s in markets.keys() if s.endswith('/USDT')]
        valid_symbols = []
        
        for symbol in usdt_symbols:
            try:
                ticker = await exchange.fetch_ticker(symbol)
                volume_usd = ticker.get('quoteVolume', 0)
                if volume_usd >= MIN_VOLUME_USD:
                    valid_symbols.append(symbol)
                await asyncio.sleep(0.05)  # Reduced delay for faster fetching
            except Exception as e:
                logger.error(f"Error fetching ticker for {symbol}: {e}")
                continue
        
        logger.info(f"Selected {len(valid_symbols)} USDT pairs with volume >= ${MIN_VOLUME_USD}")
        return valid_symbols
    except Exception as e:
        logger.error(f"Error fetching symbols: {e}")
        return []
    finally:
        await exchange.close()

# Scan symbols for signals
async def scan_symbols():
    exchange = ccxt.binance({
        'apiKey': os.getenv("BINANCE_API_KEY"),
        'secret': os.getenv("BINANCE_API_SECRET"),
        'enableRateLimit': True,
    })

    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    if not api_key or not api_secret:
        logger.error("API Key or Secret is missing! Check Koyeb Config Vars.")
        return

    try:
        # Test connection
        try:
            await exchange.fetch_ticker('BTC/USDT')
            logger.info("Binance API connection successful.")
        except Exception as e:
            logger.error(f"Binance API connection failed: {e}")
            return

        # Get valid USDT symbols
        symbols = await get_valid_symbols(exchange)
        if not symbols:
            logger.error("No valid USDT symbols found!")
            return

        for symbol in symbols:
            # Check cooldown period
            if symbol in last_signal_time:
                last_time = last_signal_time[symbol]
                if datetime.now(tz=ZoneInfo("Asia/Karachi")) < last_time + timedelta(minutes=COOLDOWN_MINUTES):
                    logger.info(f"[{symbol}] Skipped - In cooldown period")
                    continue

            # Create a new exchange instance for each symbol to avoid memory leaks
            exchange = ccxt.binance({
                'apiKey': os.getenv("BINANCE_API_KEY"),
                'secret': os.getenv("BINANCE_API_SECRET"),
                'enableRateLimit': True,
            })
            try:
                result = await analyze_symbol(exchange, symbol)
                if not result:
                    logger.info(f"⚠️ {symbol} - No valid signal")
                    continue

                confidence = result.get("confidence", 0)
                tp1_possibility = result.get("tp1_possibility", 0)
                direction = result.get("direction", "none")
                trade_type = "Scalp" if confidence < SCALPING_CONFIDENCE_THRESHOLD else "Normal"

                logger.info(
                    f"🔍 {symbol} | Confidence: {confidence:.2f} | "
                    f"Direction: {direction} | TP1 Chance: {tp1_possibility:.2f}"
                )

                if confidence >= CONFIDENCE_THRESHOLD and tp1_possibility >= TP1_POSSIBILITY_THRESHOLD:
                    # Calculate support/resistance and other metrics
                    ohlcv = await exchange.fetch_ohlcv(symbol, result["timeframe"], limit=50)
                    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"], dtype="float32")
                    df = find_support_resistance(df)
                    support = df["support"].iloc[-1] if "support" in df else 0.0
                    resistance = df["resistance"].iloc[-1] if "resistance" in df else 0.0
                    atr = (df["high"] - df["low"]).rolling(window=14).mean().iloc[-1]
                    leverage = 10 if trade_type == "Scalp" else 5

                    # Format message with emojis and PKT time
                    pk_time = datetime.now(tz=ZoneInfo("Asia/Karachi")).strftime("%Y-%m-%d %H:%M")
                    message = (
                        f"⚡ Trade Pair: {symbol}\n"
                        f"📉 Trade Type: {trade_type}\n"
                        f"🎯 Direction: {direction}\n"
                        f"🚀 Entry: {result['entry']:.2f}\n"
                        f"🎯 TP1: {result['tp1']:.2f} ({result['tp1_possibility']*100:.2f}%)\n"
                        f"💰 TP2: {result['tp2']:.2f} ({result['tp2_possibility']*100:.2f}%)\n"
                        f"📈 TP3: {result['tp3']:.2f} ({result['tp3_possibility']*100:.2f}%)\n"
                        f"🛡️ SL: {result['sl']:.2f}\n"
                        f"📊 Confidence: {confidence:.2f}%\n"
                        f"⏰ Time: {pk_time}"
                    )
                    await send_telegram_message(message)
                    # Log signal to CSV
                    log_signal_to_csv(result, trade_type, atr, leverage, support, resistance, (support + resistance) / 2, direction)
                    # Update last signal time
                    last_signal_time[symbol] = datetime.now(tz=ZoneInfo("Asia/Karachi"))
                    logger.info("✅ Signal SENT ✅")
                elif confidence < CONFIDENCE_THRESHOLD:
                    logger.info("⚠️ Skipped - Low confidence")
                elif tp1_possibility < TP1_POSSIBILITY_THRESHOLD:
                    logger.info("⚠️ Skipped - Low TP1 possibility")

                logger.info("---")
                await asyncio.sleep(0.6)  # Delay to reduce API rate limits
                df = None  # Clear DataFrame to free memory

            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                if "predict_signal" in str(e).lower() or "missing 1 required positional argument" in str(e).lower():
                    logger.info(f"⚠️ Skipped {symbol} due to prediction error, continuing to next symbol")
                    continue
                if "rate limit" in str(e).lower():
                    await asyncio.sleep(5)  # Wait on rate limit error
            finally:
                await exchange.close()

    except Exception as e:
        logger.error(f"Error in scan_symbols: {e}")
    finally:
        await exchange.close()

# Continuous scanner
async def run_bot():
    while True:
        try:
            await scan_symbols()
            logger.info(f"Completed one scan cycle, waiting {SCAN_INTERVAL_SECONDS/60} minutes for next scan")
            await asyncio.sleep(SCAN_INTERVAL_SECONDS)  # Scan every 30 minutes
        except Exception as e:
            logger.error(f"Error in run_bot: {e}")
            await asyncio.sleep(10)  # Short delay on error

# Start scanner on app startup
@app.on_event("startup")
async def start_bot():
    await asyncio.sleep(10)  # Delay to ensure app is fully initialized
    asyncio.create_task(run_bot())

# Run app
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
