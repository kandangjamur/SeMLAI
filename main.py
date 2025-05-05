import asyncio
import ccxt.async_support as ccxt
from fastapi import FastAPI
from core.engine import run_engine
from utils.logger import log
import uvicorn

app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

async def main():
    exchange = ccxt.binance({"enableRateLimit": True})
    try:
        while True:
            await run_engine()
            log("Waiting 60 seconds before next scan...")
            await asyncio.sleep(60)
    except Exception as e:
        log(f"Bot task cancelled: {e}", level='INFO')
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(main())
    uvicorn.run(app, host="0.0.0.0", port=8000)
