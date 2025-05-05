import threading
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

def start_engine():
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    while True:
        try:
            loop.run_until_complete(run_engine())
            log("Waiting 60 seconds before next scan...")
            loop.run_until_complete(asyncio.sleep(60))
        except Exception as e:
            log(f"Error in engine loop: {e}", level='ERROR')
            loop.run_until_complete(asyncio.sleep(10))

if __name__ == "__main__":
    # Log initial memory and CPU usage
    memory = psutil.Process().memory_info().rss / 1024 / 1024
    cpu_percent = psutil.cpu_percent(interval=0.1)
    log(f"Initial - Memory: {memory:.2f} MB, CPU: {cpu_percent:.1f}%")

    # Start engine in a separate thread
    engine_thread = threading.Thread(target=start_engine, daemon=True)
    engine_thread.start()

    # Run uvicorn server
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1, timeout_keep_alive=240)
