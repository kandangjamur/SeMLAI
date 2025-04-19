import pandas as pd
from flask import Flask
from threading import Thread
from telebot.bot import send_signal
from core.analysis import run_analysis_loop
from core.news_sentiment import start_sentiment_stream
from telebot.report_generator import generate_daily_summary
from data.tracker import update_signal_status
from utils.logger import log
from datetime import datetime
import time

app = Flask(__name__)

@app.route("/")
def home():
    return "Crypto Sniper AI Bot is Live!"

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

if __name__ == "__main__":
    log("🚀 Starting Crypto Sniper...")
    try:
        Thread(target=run_analysis_loop).start()
        Thread(target=start_sentiment_stream).start()
        Thread(target=daily_report_loop).start()
        Thread(target=tracker_loop).start()
        Thread(target=heartbeat).start()
        app.run(host="0.0.0.0", port=8000)
    except Exception as e:
        log(f"❌ Main Crash: {e}")
