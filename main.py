# main.py
import os
import time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from threading import Thread
from datetime import datetime
from telebot.bot import start_telegram_bot
from core.analysis import run_analysis_loop
from core.news_sentiment import start_sentiment_stream
from telebot.report_generator import generate_daily_summary
from data.tracker import update_signal_status
from utils.logger import log
import pandas as pd

app = FastAPI()

# Setup Jinja2 Templates
templates_dir = os.path.join(os.path.dirname(__file__), "dashboard/templates")
env = Environment(loader=FileSystemLoader(templates_dir))

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
    
    template = env.get_template("dashboard.html")
    return template.render(content=html_table)

# Threads
def daily_report_loop():
    while True:
        now = datetime.now()
        if now.hour == 23 and now.minute == 59:
            generate_daily_summary()
        time.sleep(60)

def tracker_loop():
    while True:
        update_signal_status()
        time.sleep(600)

def heartbeat():
    while True:
        log("❤️ Still alive - Sniper running...")
        time.sleep(300)

# Run Everything
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
