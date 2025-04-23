# main.py
import os
import time
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from threading import Thread
from datetime import datetime
from telebot.bot import start_telegram_bot
from core.analysis import run_analysis_loop
from core.news_sentiment import start_sentiment_stream
from telebot.report_generator import generate_daily_summary
from data.tracker import update_signal_status
from utils.logger import log

app = FastAPI()

# Auto-create required dashboard folders
if not os.path.exists("dashboard/static"):
    os.makedirs("dashboard/static")
if not os.path.exists("dashboard/templates"):
    os.makedirs("dashboard/templates")

# Jinja2 Templates Setup
templates_dir = os.path.join("dashboard", "templates")
env = Environment(loader=FileSystemLoader(templates_dir))

# Mount static folder
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    update_signal_status()
    try:
        df = pd.read_csv("logs/signals_log.csv")
        df = df.sort_values(by="timestamp", ascending=False)
        html_table = df.to_html(index=False, classes="table table-striped", escape=False)
    except Exception as e:
        html_table = f"<p>Error loading log: {e}</p>"

    try:
        template = env.get_template("dashboard.html")
        return template.render(content=html_table)
    except TemplateNotFound:
        return HTMLResponse("<h2>Error: dashboard.html not found in dashboard/templates</h2>", status_code=500)

# Scheduled daily Telegram report
def daily_report_loop():
    while True:
        now = datetime.now()
        if now.hour == 23 and now.minute == 59:
            try:
                generate_daily_summary()
                log("📊 Daily report generated.")
            except Exception as e:
                log(f"❌ Daily report error: {e}")
        time.sleep(60)

def tracker_loop():
    while True:
        try:
            update_signal_status()
        except Exception as e:
            log(f"❌ Tracker update error: {e}")
        time.sleep(600)

def heartbeat():
    while True:
        log("❤️ Still alive - Sniper running...")
        time.sleep(300)

# Run all threads
if __name__ == "__main__":
    log("🚀 Starting Crypto Sniper...")

    try:
        Thread(target=start_telegram_bot).start()
        Thread(target=run_analysis_loop).start()
        Thread(target=start_sentiment_stream).start()
        Thread(target=daily_report_loop).start()
        Thread(target=tracker_loop).start()
        Thread(target=heartbeat).start()

        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)

    except Exception as e:
        log(f"❌ Main Crash: {e}")
