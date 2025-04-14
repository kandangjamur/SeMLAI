from flask import Flask
from threading import Thread
from telebot.bot import start_telegram_bot  # ✅ updated import
from core.analysis import run_analysis_loop
from core.news_sentiment import start_sentiment_stream
from utils.logger import log

app = Flask(__name__)

@app.route("/")
def home():
    return "Crypto Sniper AI Bot is Live!"

if __name__ == "__main__":
    log("🚀 Starting Crypto Sniper...")
    Thread(target=start_telegram_bot).start()
    Thread(target=run_analysis_loop).start()
    Thread(target=start_sentiment_stream).start()
    app.run(host="0.0.0.0", port=8000)
