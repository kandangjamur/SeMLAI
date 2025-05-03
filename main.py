import asyncio
import uvicorn
from fastapi import FastAPI
from utils.logger import setup_logger
from core.analysis import get_valid_symbols, analyze_symbol
from telebot.sender import send_telegram_signal
import signal

logger = setup_logger()
app = FastAPI()

CONFIDENCE_THRESHOLD = 50

stop_event = asyncio.Event()


@app.on_event("startup")
async def startup_event():
    logger.info("🚀 App starting up...")
    asyncio.create_task(start_signal_loop())
    asyncio.create_task(keep_alive_loop())


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.on_event("shutdown")
async def shutdown_event():
    stop_event.set()
    logger.info("Signal scanning loop cancelled gracefully.")


async def keep_alive_loop():
    while not stop_event.is_set():
        try:
            logger.info("💓 Keep-alive ping sent.")
            await asyncio.sleep(15)
        except Exception as e:
            logger.warning(f"Keep-alive loop error: {e}")


async def start_signal_loop():
    await asyncio.sleep(2)  # Allow app to stabilize
    symbols = await get_valid_symbols()
    logger.info(f"✅ Loaded {len(symbols)} symbols. Starting scan and keep-alive tasks...")

    while not stop_event.is_set():
        logger.info("📊 Scanning symbols...")
        for symbol in symbols:
            try:
                signal_data = await analyze_symbol(symbol)
                if not signal_data:
                    continue

                direction = signal_data.get("direction")
                confidence = signal_data.get("confidence")
                tp1_possibility = signal_data.get("tp1_possibility")

                log_msg = f"🔍 {symbol} | Confidence: {confidence:.2f} | Direction: {direction} | TP1 Chance: {tp1_possibility:.2f}"

                if confidence < CONFIDENCE_THRESHOLD:
                    logger.info(f"{log_msg}\n⚠️ Skipped - Low confidence\n---")
                    continue
                if tp1_possibility < 0.5:
                    logger.info(f"{log_msg}\n⚠️ Skipped - Low TP1 possibility\n---")
                    continue

                await send_telegram_signal(symbol, direction, confidence, tp1_possibility)
                logger.info(f"{log_msg}\n✅ Signal SENT ✅\n---")

            except Exception as e:
                logger.error(f"Error scanning {symbol}: {e}")

        logger.info("⏳ Sleeping 30s before next scan...")
        await asyncio.sleep(30)


def graceful_exit(*args):
    stop_event.set()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, graceful_exit)
    signal.signal(signal.SIGTERM, graceful_exit)
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
