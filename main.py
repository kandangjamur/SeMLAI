import asyncio
import uvicorn
from fastapi import FastAPI
from utils.logger import setup_logger
from core.analysis import analyze_market
import ccxt.async_support as ccxt

logger = setup_logger("Main")
app = FastAPI()

CONFIDENCE_THRESHOLD = 70

exchange = None
symbol_list = []

@app.on_event("startup")
async def startup_event():
    global exchange, symbol_list
    exchange = ccxt.binance()
    logger.info("Binance exchange initialized")

    try:
        markets = await exchange.load_markets()
        symbol_list = [s for s in markets if s.endswith("/USDT") and markets[s]["active"]]
        if not symbol_list:
            symbol_list = [s for s in markets if s.endswith("/BTC") and markets[s]["active"]]
            logger.warning("No USDT pairs found. Falling back to BTC pairs.")
        logger.info(f"Loaded {len(symbol_list)} valid symbols")
    except Exception as e:
        logger.error(f"Error loading markets: {e}")
        await shutdown_event()

@app.on_event("shutdown")
async def shutdown_event():
    if exchange:
        await exchange.close()
        logger.info("Exchange connection closed.")

@app.get("/health")
def health_check():
    return {"status": "ok"}

async def scan_loop():
    while True:
        try:
            await analyze_market(exchange, symbol_list, CONFIDENCE_THRESHOLD)
        except Exception as e:
            logger.error(f"Error in scan loop: {e}")
        await asyncio.sleep(10)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(scan_loop())
    uvicorn.run(app, host="0.0.0.0", port=8000)
