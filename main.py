import asyncio
import uvicorn
from fastapi import FastAPI
from core.analysis import analyze_symbol
from core.indicators import load_price_data, get_valid_symbols
from utils.logger import setup_logger
from telebot.sender import send_telegram_message

logger = setup_logger("scanner")
app = FastAPI()

CONFIDENCE_THRESHOLD = 50

@app.get("/")
async def root():
    return {"message": "Bot is running."}

async def scan_symbols():
    symbols = await get_valid_symbols()
    for symbol in symbols:
        try:
            ohlcv = await load_price_data(symbol)
            if not ohlcv:
                continue

            result = await analyze_symbol(symbol, ohlcv)
            if not result:
                continue

            confidence = result["confidence"]
            tp1_possibility = result["tp1_possibility"]
            direction = result["direction"]

            print(f"🔍 {symbol} | Confidence: {confidence:.2f} | Direction: {direction} | TP1 Chance: {tp1_possibility:.2f}")

            if confidence >= CONFIDENCE_THRESHOLD and tp1_possibility >= 0.5:
                message = f"🚀 {symbol}\nDirection: {direction}\nConfidence: {confidence:.2f}\nTP1 Possibility: {tp1_possibility:.2f}"
                await send_telegram_message(message)
                print("✅ Signal SENT ✅")
            elif confidence < CONFIDENCE_THRESHOLD:
                print("⚠️ Skipped - Low confidence")
            elif tp1_possibility < 0.5:
                print("⚠️ Skipped - Low TP1 possibility")

            print("---")

        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")

async def run_bot():
    while True:
        await scan_symbols()
        await asyncio.sleep(60)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(run_bot())
    uvicorn.run(app, host="0.0.0.0", port=8000)
