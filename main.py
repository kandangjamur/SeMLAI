import asyncio
import ccxt.async_support as ccxt
from fastapi import FastAPI
from core.engine import run_engine
from utils.logger import log
import psutil
import uvicorn

app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

async def main():
    # Log initial memory and CPU usage
    memory = psutil.Process().memory_info().rss / 1024 / 1024
    cpu_percent = psutil.cpu_percent(interval=0.1)
    log(f"Initial - Memory: {memory:.2f} MB, CPU: {cpu_percent:.1f}%")

    while True:
        await run_engine()
        log("Waiting 60 seconds before next scan...")
        await asyncio.sleep(60)

if __name__ == "__main__":
    # Run engine as a background task
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1, timeout_keep_alive=240)
