import asyncio
import ccxt.async_support as ccxt
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from core.engine import run_engine
from utils.logger import log
import psutil
import uvicorn
import os

app = FastAPI()
templates = Jinja2Templates(directory="dashboard/templates")

@app.get("/health")
async def health_check():
    log("[Health Check] Accessed /health endpoint")
    return {"status": "healthy"}

@app.get("/")
async def dashboard(request: Request):
    try:
        memory = psutil.Process().memory_info().rss / 1024 / 1024
        cpu_percent = psutil.cpu_percent(interval=0.1)
        log(f"[Main Dashboard] Loading dashboard - Memory: {memory:.2f} MB, CPU: {cpu_percent:.1f}%")

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
        memory = psutil.Process().memory_info().rss / 1024 / 1024
        cpu_percent = psutil.cpu_percent(interval=0.1)
        log(f"[Main] Initializing main loop - Memory: {memory:.2f} MB, CPU: {cpu_percent:.1f}%")

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
