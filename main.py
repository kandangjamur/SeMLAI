import asyncio
import ccxt.async_support as ccxt
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from core.engine import run_engine
from utils.logger import log
import psutil
import uvicorn
import os

log("[Main] File loaded: main.py")  # Confirm file loading

app = FastAPI()
templates = Jinja2Templates(directory="dashboard/templates")

@app.get("/health")
async def health_check():
    log("[Health Check] Accessed /health endpoint")
    return {"status": "healthy"}

@app.get("/")
async def dashboard(request: Request):
    try:
        log("[Main Dashboard] Loading dashboard")
        memory = psutil.Process().memory_info().rss / 1024 / 1024
        cpu_percent = psutil.cpu_percent(interval=0.1)
        log(f"[Main Dashboard] Memory: {memory:.2f} MB, CPU: {cpu_percent:.1f}%")

        template_path = "dashboard/templates/dashboard.html"
        log(f"[Main Dashboard] Checking template at {template_path}")
        if not os.path.exists(template_path):
            log(f"[Main Dashboard] Template not found at {template_path}", level='ERROR')
            return {"error": "Dashboard template not found"}

        log(f"[Main Dashboard] Rendering template: {template_path}")
        return templates.TemplateResponse("dashboard.html", {"request": request})
    except Exception as e:
        log(f"[Main Dashboard] Error in dashboard: {str(e)}", level='ERROR')
        return {"error": f"Dashboard error: {str(e)}"}

async def main():
    try:
        log("[Main] Initializing main loop")
        memory = psutil.Process().memory_info().rss / 1024 / 1024
        cpu_percent = psutil.cpu_percent(interval=0.1)
        log(f"[Main] Memory: {memory:.2f} MB, CPU: {cpu_percent:.1f}%")

        while True:
            log("[Main] Starting run_engine iteration")
            await run_engine()
            log("[Main] run_engine iteration completed, waiting 60 seconds")
            await asyncio.sleep(60)
    except Exception as e:
        log(f"[Main] Error in main loop: {str(e)}", level='ERROR')
        await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        log("[Main] Starting application")
        memory = psutil.Process().memory_info().rss / 1024 / 1024
        log(f"[Main] Application startup - Memory: {memory:.2f} MB")

        log("[Main] Checking environment variables")
        required_vars = ["BINANCE_API_KEY", "BINANCE_API_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
        for var in required_vars:
            if not os.getenv(var):
                log(f"[Main] Missing environment variable: {var}", level='ERROR')
                raise ValueError(f"Missing environment variable: {var}")

        log("[Main] Checking required files")
        model_path = "models/rf_model.joblib"
        if not os.path.exists(model_path):
            log(f"[Main] Model file not found at {model_path}", level='ERROR')
            raise FileNotFoundError(f"Model file not found: {model_path}")

        template_path = "dashboard/templates/dashboard.html"
        if not os.path.exists(template_path):
            log(f"[Main] Template file not found at {template_path}", level='ERROR')
            raise FileNotFoundError(f"Template file not found: {template_path}")

        log("[Main] Creating event loop")
        loop = asyncio.get_event_loop()
        log("[Main] Event loop created")

        log("[Main] Creating task for main")
        loop.create_task(main())
        log("[Main] Task created for main")

        log("[Main] Starting uvicorn server")
        uvicorn.run(app, host="0.0.0.0", port=8000, workers=1, timeout_keep_alive=240)
        log("[Main] Uvicorn server started")
    except Exception as e:
        log(f"[Main] Error starting application: {str(e)}", level='ERROR')
        raise
