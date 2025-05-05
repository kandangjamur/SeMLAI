from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from utils.logger import log
import psutil
import os

app = FastAPI()
templates = Jinja2Templates(directory="dashboard/templates")

@app.get("/")
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
