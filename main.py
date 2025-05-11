import asyncio
import uvicorn
from fastapi import FastAPI
from core.analysis import analyze_symbol, initialize_predictor
import ccxt.async_support as ccxt
import os
import logging
import pandas as pd
from dotenv import load_dotenv
import telegram
from utils.support_resistance import find_support_resistance
from utils.logger import log
from datetime import datetime, timedelta
import pytz
import gc

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
CONFIDENCE_THRESHOLD = 65  # 65% for tight thresholds
TP1_POSSIBILITY_THRESHOLD = 0.65  # 65%
SCALPING_CONFIDENCE_THRESHOLD = 80
MIN_VOLUME_USD = 1000000  # Filter low liquidity coins
COOLDOWN_MINUTES = 30
SCAN_INTERVAL_SECONDS = 1800

# Blacklist delisted or low liquidity coins
BLACKLISTED_SYMBOLS = [
    'VEN/USDT', 'PAX/USDT', 'BCHABC/USDT', 'BADGER/USDT', 'BAL/USDT',
    'CREAM/USDT', 'NULS/USDT', 'TROY/USDT'
]

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
            "timestamp": pd.Timestamp.now(tz=pytz.timezone("Asia/Karachi")).isoformat(),
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
            "status": "open"
        }
        df = pd.DataFrame([signal_data])
        BACKTEST_FILE = "logs/signals_log_new.csv"
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

# Get valid USDT pairs with sufficient volume and filter delisted coins
async def get_valid_symbols(exchange):
    try:
        markets = await exchange.load_markets()
        usdt_symbols = [
            symbol for symbol in markets
            if symbol.endswith('/USDT') and markets[symbol]['active'] and markets[symbol]['info']['status'] == 'TRADING'
        ]
        valid_symbols = []
        
        for symbol in usdt_symbols:
            if symbol in BLACKLISTED_SYMBOLS:
                continue
            try:
                ticker = await exchange.fetch_ticker(symbol)
                volume_usd = ticker.get('quoteVolume', 0)
                if volume_usd >= MIN_VOLUME_USD:
                    valid_symbols.append(symbol)
                await asyncio.sleep(0.07)
            except Exception as e:
                logger.error(f"Error fetching ticker for {symbol}: {e}")
                continue
        
        logger.info(f"Selected {len(valid_symbols)} USDT pairs with volume >= ${MIN_VOLUME_USD}")
        return valid_symbols[:150]  # Limit to 150 symbols
    except Exception as e:
        logger.error(f"Error fetching symbols: {e}")
        return []
    finally:
        await exchange.close()

# Scan symbols for signals
async def scan_symbols():
    try:
        # Create exchange for initial setup
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

        # Test connection
        try:
            await exchange.fetch_ticker('BTC/USDT')
            logger.info("Binance API connection successful.")
        except Exception as e:
            logger.error(f"Binance API connection failed: {e}")
            return
        finally:
            await exchange.close()

        # Get valid USDT symbols
        exchange = ccxt.binance({
            'apiKey': os.getenv("BINANCE_API_KEY"),
            'secret': os.getenv("BINANCE_API_SECRET"),
            'enableRateLimit': True,
        })
        symbols = await get_valid_symbols(exchange)
        logger.info(f"Scanning {len(symbols)} symbols (limited to 150)")
        if not symbols:
            logger.error("No valid USDT symbols found!")
            return

        for symbol in symbols:
            if symbol in last_signal_time:
                last_time = last_signal_time[symbol]
                if datetime.now(tz=pytz.timezone("Asia/Karachi")) < last_time + timedelta(minutes=COOLDOWN_MINUTES):
                    logger.info(f"[{symbol}] Skipped - In cooldown period")
                    continue

            # Create new exchange instance for each symbol
            exchange = ccxt.binance({
                'apiKey': os.getenv("BINANCE_API_KEY"),
                'secret': os.getenv("BINANCE_API_SECRET"),
                'enableRateLimit': True,
            })
            df = None
            try:
                result = await analyzeocomplete_symbol(exchange, symbol)
                if not result or not isinstance(result, dict):
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

                # Fetch OHLCV for support/resistance
                ohlcv = await exchange.fetch_ohlcv(symbol, result["timeframe"], limit=50)
                df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"], dtype="float32")
                if df.empty or len(df) < 10:
                    logger.warning(f"[{symbol}] Insufficient OHLCV data, skipping")
                    continue
                df = find_support_resistance(df)
                
                # Ensure support/resistance are valid
                support = df["support"].iloc[-1] if "support" in df and not pd.isna(df["support"].iloc[-1]) else df["low"].iloc[-1]
                resistance = df["resistance"].iloc[-1] if "resistance" in df and not pd.isna(df["resistance"].iloc[-1]) else df["high"].iloc[-1]
                atr = (df["high"] - df["low"]).rolling(window=14).mean().iloc[-1]
                if pd.isna(atr) or atr <= 0:
                    logger.warning(f"[{symbol]] Invalid ATR, skipping")
                    continue
                leverage = 10 if trade_type == "Scalp" else 5

                if confidence >= CONFIDENCE_THRESHOLD and tp1_possibility >= TP1_POSSIBILITY_THRESHOLD:
                    pk_time = datetime.now(tz=pytz.timezone("Asia/Karachi")).strftime("%Y-%m-%d %H:%M")
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
                    log_signal_to_csv(result, trade_type, atr, leverage, support, resistance, (support + resistance) / 2, direction)
                    last_signal_time[symbol] = datetime.now(tz=pytz.timezone("Asia/Karachi"))
                    logger.info("✅ Signal SENT ✅")
                elif confidence < CONFIDENCE_THRESHOLD:
                    logger.info("⚠️ Skipped - Low confidence")
                elif tp1_possibility < TP1_POSSIBILITY_THRESHOLD:
                    logger.info("⚠️ Skipped - Low TP1 possibility")

                logger.info("---")
                await asyncio.sleep(1.0)  # Reduce CPU load

            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                if "rate limit" in str(e).lower():
                    await asyncio.sleep(5)
                logger.info(f"⚠️ Skipped {symbol} due to error, continuing to next symbol")
                continue
            finally:
                if df is not None:
                    del df
                await exchange.close()
                gc.collect()

    except Exception as e:
        logger.error(f"Error in scan_symbols: {e}")
    finally:
        gc.collect()

# Continuous scanner
async def run_bot():
    while True:
        try:
            await scan_symbols()
            logger.info(f"Completed one scan cycle, waiting {SCAN_INTERVAL_SECONDS/60} minutes for next scan")
            await asyncio.sleep(SCAN_INTERVAL_SECONDS)
        except Exception as e:
            logger.error(f"Error in run_bot: {e}")
            await asyncio.sleep(10)

# Start scanner on app startup
@app.on_event("startup")
async def start_bot():
    await initialize_predictor()
    await asyncio.sleep(10)
    asyncio.create_task(run_bot())

# Run app
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
