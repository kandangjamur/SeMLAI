import asyncio
import time
import uvicorn
import traceback
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from core.analysis import analyze_symbol
from utils.logger import setup_logger
from core.indicators import get_usdt_symbols, get_binance_exchange, exchange

logger = setup_logger("main")
app = FastAPI()

origins = ["*"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

active_signals = {}
CONFIDENCE_THRESHOLD = 50
API_DELAY = 0.4
SYMBOL_LIMIT = 6

@app.on_event("shutdown")
async def shutdown_event():
    await exchange.close()
    logger.info("Exchange connection closed.")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/scan")
async def scan():
    try:
        start = time.time()
        symbols = await get_usdt_symbols(exchange)
        logger.info(f"Loaded {len(symbols)} valid USDT symbols")

        if not symbols:
            return JSONResponse(content={"error": "No valid symbols found"}, status_code=500)

        results = []
        tasks = []

        for symbol in symbols[:SYMBOL_LIMIT]:
            tasks.append(analyze_symbol(exchange, symbol))

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for result in responses:
            if isinstance(result, Exception):
                logger.error(f"Error during symbol analysis: {traceback.format_exc()}")
                continue
            if result and result.get("confidence", 0) >= CONFIDENCE_THRESHOLD:
                direction = result["signal"]
                symbol = result["symbol"]
                key = f"{symbol}-{direction}"

                existing = active_signals.get(symbol)
                if existing and existing["signal"] != direction and not existing.get("tp1_hit"):
                    logger.info(f"Skipping opposite signal for {symbol} (active: {existing['signal']})")
                    continue

                result["timestamp"] = time.strftime('%Y-%m-%d %H:%M:%S')
                results.append(result)
                active_signals[symbol] = result

        duration = round(time.time() - start, 2)
        logger.info(f"Scan completed in {duration}s. Signals: {len(results)}")
        return results

    except Exception as e:
        logger.error(f"Unhandled exception in /scan: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
