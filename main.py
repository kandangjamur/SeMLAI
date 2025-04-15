from flask import Flask
from threading import Thread
from telebot.bot import start_telegram_bot
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

# Daily Summary Generator (at 23:59)
def daily_report_loop():
    while True:
        now = datetime.now()
        if now.hour == 23 and now.minute == 59:
            generate_daily_summary()
        time.sleep(60)

# Auto TP/SL Updater
def tracker_loop():
    while True:
        update_signal_status()
        time.sleep(600)  # Every 10 mins

if __name__ == "__main__":
    log("🚀 Starting Crypto Sniper...")
    Thread(target=start_telegram_bot).start()
    Thread(target=run_analysis_loop).start()
    Thread(target=start_sentiment_stream).start()
    Thread(target=daily_report_loop).start()
    Thread(target=tracker_loop).start()
    app.run(host="0.0.0.0", port=8000)
