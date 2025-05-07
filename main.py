import os
import sys
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from utils.logger import log
import uvicorn
import psutil

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

if __name__ == "__main__":
    try:
        log("[Main] Entering __main__ block")
        memory = psutil.Process().memory_info().rss / 1024 / 1024
        log(f"[Main] Application startup - Memory: {memory:.2f} MB")

        log("[Main] Checking environment variables")
        required_vars = ["BINANCE_API_KEY", "BINANCE_API_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
        for var in required_vars:
            value = os.getenv(var)
            log(f"[Main] Env var {var}: {'Set' if value else 'Missing'}")
            if not value:
                log(f"[Main] Missing environment variable: {var}", level='ERROR')
                raise ValueError(f"Missing environment variable: {var}")

        log("[Main] Checking required files")
        model_path = "models/rf_model.joblib"
        log(f"[Main] Checking file: {model_path}")
        if not os.path.exists(model_path):
            log(f"[Main] Model file not found at {model_path}", level='ERROR')
            raise FileNotFoundError(f"Model file not found: {model_path}")

        template_path = "dashboard/templates/dashboard.html"
        log(f"[Main] Checking file: {template_path}")
        if not os.path.exists(template_path):
            log(f"[Main] Template file not found at {template_path}", level='ERROR')
            raise FileNotFoundError(f"Template file not found: {template_path}")

        log("[Main] Starting uvicorn server")
        uvicorn.run(app, host="0.0.0.0", port=8000, workers=1, timeout_keep_alive=240)
        log("[Main] Uvicorn server started")
    except Exception as e:
        log(f"[Main] Error in __main__ block: {str(e)}", level='ERROR')
        sys.exit(1)
