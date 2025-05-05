import asyncio
import ccxt.async_support as ccxt
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from core.engine import run_engine
from utils.logger import log
import psutil
import uvicorn
from dashboard.app import app as dashboard_app

app = FastAPI()
app.mount("/dashboard", dashboard_app)
templates = Jinja2Templates(directory="dashboard/templates")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/")
async def root():
    # Log memory and CPU usage
    memory = psutil.Process().memory_info().rss / 1024 / 1024
    cpu_percent = psutil.cpu_percent(interval=0.1)
    log(f"[Root] Loading - Memory: {memory:.2f} MB, CPU: {cpu_percent:.1f}%")
    return {"message": "Redirecting to /dashboard"}

async def main():
    # Log initial memory and CPU usage
    memory = psutil.Process().memory_info().rss / 1024 / 1024
    cpu_percent = psutil.cpu_percent(interval=0.1)
    log(f"Initial - Memory: {memory:.2f} MB, CPU: {cpu_percent:.1f}%")

    while True:
        try:
            await run_engine()
            log("Waiting 60 seconds before next scan...")
            await asyncio.sleep(60)
        except Exception as e:
            log(f"Error in main loop: {e}", level='ERROR')
            await asyncio.sleep(10)

if __name__ == "__main__":
    # Run engine as a background task
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1, timeout_keep_alive=240)
