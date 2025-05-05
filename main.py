import asyncio
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
    return {"status": "healthy"}

@app.get("/dashboard")
async def dashboard(request: Request):
    try:
        # Log memory and CPU usage
        memory = psutil.Process().memory_info().rss / 1024 / 1024
        cpu_percent = psutil.cpu_percent(interval=0.1)
        log(f"[Dashboard] Loading - Memory: {memory:.2f} MB, CPU: {cpu_percent:.1f}%")

        if not os.path.exists("dashboard/templates/dashboard.html"):
            log("Dashboard template 'dashboard.html' not found", level='ERROR')
            return {"error": "Dashboard template not found"}

        return templates.TemplateResponse("dashboard.html", {"request": request})
    except Exception as e:
        log(f"[Dashboard] Error loading dashboard: {e}", level='ERROR')
        return {"error": str(e)}

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
    # Run engine in the same event loop
    asyncio.run(main())
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1, timeout_keep_alive=240)
