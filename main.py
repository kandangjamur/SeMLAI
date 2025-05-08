import asyncio
import uvicorn
from fastapi import FastAPI
from core.analysis import analyze_symbol
import ccxt.async_support as ccxt
import os
import logging
from dotenv import load_dotenv
import telegram

# لاگنگ سیٹ اپ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("scanner")

# .env فائل سے ویری ایبل لوڈ کرو
load_dotenv()

# FastAPI ایپ
app = FastAPI()
bot_task = None  # Task reference محفوظ رکھنے کے لیے

# ٹیلیگرام فنکشن
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

@app.get("/")
async def root():
    return {"message": "Crypto Signal Bot is running."}

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Bot is operational."}

@app.get("/ping")
async def ping():
    return {"message": "pong"}

# Valid USDT symbols
async def get_valid_symbols(exchange):
    try:
        markets = await exchange.load_markets()
        usdt_symbols = [s for s in markets.keys() if s.endswith('/USDT')]
        logger.info(f"Found {len(usdt_symbols)} USDT pairs")
        return usdt_symbols
    except Exception as e:
        logger.error(f"Error fetching symbols: {e}")
        return []
    finally:
        await exchange.close()

# سگنل سکین فنکشن
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
        try:
            await exchange.fetch_ticker('BTC/USDT')
            logger.info("Binance API connection successful.")
        except Exception as e:
            logger.error(f"Binance API connection failed: {e}")
            return

        symbols = await get_valid_symbols(exchange)
        if not symbols:
            logger.error("No valid USDT symbols found!")
            return

        for symbol in symbols:
            try:
                result = await analyze_symbol(exchange, symbol)
                if not result or not result.get('direction'):
                    logger.info(f"⚠️ {symbol} - No valid signal")
                    logger.info("---")
                    continue

                confidence = result.get("confidence", 0)
                direction = result.get("direction", "none")
                tp1_possibility = 0.75  # ڈمی ویلیو

                trade_type = "Scalping" if confidence < 85 else "Normal"

                logger.info(
                    f"🔍 {symbol} | Confidence: {confidence:.2f} | "
                    f"Direction: {direction} | TP1 Chance: {tp1_possibility:.2f}"
                )

                message = (
                    f"🚀 {symbol}\n"
                    f"Trade Type: {trade_type}\n"
                    f"Direction: {direction}\n"
                    f"Entry: {result['entry']:.4f}\n"
                    f"TP1: {result['tp1']:.4f}\n"
                    f"TP2: {result['tp2']:.4f}\n"
                    f"TP3: {result['tp3']:.4f}\n"
                    f"SL: {result['sl']:.4f}\n"
                    f"Confidence: {confidence:.2f}\n"
                    f"TP1 Possibility: {tp1_possibility:.2f}"
                )
                await send_telegram_message(message)
                logger.info("✅ Signal SENT ✅")
                logger.info("---")

            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                logger.info("---")

    except Exception as e:
        logger.error(f"Error in scan_symbols: {e}")
    finally:
        await exchange.close()

# مسلسل سکینر
async def run_bot():
    while True:
        try:
            await scan_symbols()
        except Exception as e:
            logger.error(f"Error in run_bot: {e}")
        await asyncio.sleep(60)

# ایپ کے شروع ہوتے ہی بوٹ اسٹارٹ
@app.on_event("startup")
async def start_bot():
    global bot_task
    bot_task = asyncio.ensure_future(run_bot())  # task reference محفوظ رکھیں

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
