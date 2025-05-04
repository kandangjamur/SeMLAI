import asyncio
import uvicorn
from fastapi import FastAPI
from core.analysis import fetch_ohlcv, analyze_symbol
from core.indicators import calculate_indicators
from utils.logger import setup_logger
from telebot.sender import send_telegram_message
import ccxt.async_support as ccxt
import os
from dotenv import load_dotenv

# ماحولیاتی متغیرات لوڈ کرو
load_dotenv()

# لاگر سیٹ اپ کرو
logger = setup_logger("scanner")

# FastAPI ایپ
app = FastAPI()

# کنفیڈنس اور TP1 کی حد (درستگی کے لیے سخت کیا)
CONFIDENCE_THRESHOLD = 70  # 70% سے زیادہ کنفیڈنس والے سگنلز
TP1_POSSIBILITY_THRESHOLD = 0.7  # 70% سے زیادہ TP1 امکان

# ہیلتھ چیک اینڈ پوائنٹ
@app.get("/")
async def root():
    return {"message": "Bot is running."}

# بائننس سے تمام USDT پیئرز لینے کا فنکشن
async def get_valid_symbols(exchange):
    try:
        markets = await exchange.load_markets()
        # صرف USDT پیئرز فلٹر کرو
        usdt_symbols = [s for s in markets.keys() if s.endswith('/USDT')]
        logger.info(f"Found {len(usdtiprocessing symbols)} USDT pairs")
        return usdt_symbols
    except Exception as e:
        logger.error(f"Error fetching symbols: {e}")
        return []
    finally:
        await exchange.close()

# سگنلز سکین کرنے کا فنکشن
async def scan_symbols():
    # بائننس ایکسچینج سیٹ اپ کرو
    exchange = ccxt.binance({
        'apiKey': os.getenv("BINANCE_API_KEY"),
        'secret': os.getenv("BINANCE_API_SECRET"),
    })

    # API کیز چیک کرو
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    if not api_key or not api_secret:
        logger.error("API Key or Secret is missing!")
        return

    try:
        # ٹریڈنگ پیئرز لے لو
        symbols = await get_valid_symbols(exchange)
        if not symbols:
            logger.error("No valid USDT symbols found!")
            return

        for symbol in symbols:
            try:
                # ڈیٹا اور تجزیہ کرو
                result = await analyze_symbol(exchange, symbol)
                if not result or not result.get('signal'):
                    logger.info(f"⚠️ {symbol} - No valid signal")
                    continue

                confidence = result.get("confidence", 0)
                tp1_possibility = result.get("tp1_chance", 0)
                direction = result.get("signal", "none")
                atr = result.get("atr", 0.01)

                logger.info(f"🔍 {symbol} | Confidence: {confidence:.2f} | Direction: {direction} | TP1 Chance: {tp1_possibility:.2f} | ATR: {atr:.4f}")

                # اگر کنفیڈنس اور TP1 امکان حد سے زیادہ ہو، تو میسیج بھیجو
                if confidence >= CONFIDENCE_THRESHOLD and tp1_possibility >= TP1_POSSIBILITY_THRESHOLD:
                    message = (
                        f"🚀 {symbol}\n"
                        f"Direction: {direction}\n"
                        f"Confidence: {confidence:.2f}\n"
                        f"TP1 Possibility: {tp1_possibility:.2f}\n"
                        f"ATR: {atr:.4f}"
                    )
                    await send_telegram_message(message)
                    logger.info(f"✅ Signal SENT for {symbol} ✅")
                elif confidence < CONFIDENCE_THRESHOLD:
                    logger.info(f"⚠️ {symbol} - Skipped (Low confidence: {confidence:.2f})")
                elif tp1_possibility < TP1_POSSIBILITY_THRESHOLD:
                    logger.info(f"⚠️ {symbol} - Skipped (Low TP1 possibility: {tp1_possibility:.2f})")

                logger.info("---")

            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")

    except Exception as e:
        logger.error(f"Error in scan_symbols: {e}")
    finally:
        await exchange.close()

# بٹ کو مسلسل چلانے کا فنکشن
async def run_bot():
    while True:
        await scan_symbols()
        await asyncio.sleep(60)  # ہر منٹ سکین کرو

# مین ایپلیکیشن
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(run_bot())
    uvicorn.run(app, host="0.0.0.0", port=8000)
