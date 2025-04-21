import threading
import requests
import time
from utils.logger import log
import os
from dotenv import load_dotenv

load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

# Trending coins cache
trending_coins = []

def fetch_trending_coins():
    global trending_coins
    try:
        url = "https://api.coingecko.com/api/v3/search/trending"
        res = requests.get(url)
        data = res.json()
        trending = [item["item"]["symbol"].upper() + "/USDT" for item in data["coins"]]
        trending_coins = trending
        log(f"[TRENDING] {trending_coins}")
    except Exception as e:
        log(f"❌ Trending fetch error: {e}")

def start_sentiment_stream():
    def loop():
        while True:
            fetch_trending_coins()
            time.sleep(300)  # refresh every 5 min
    thread = threading.Thread(target=loop)
    thread.daemon = True
    thread.start()

def get_sentiment_boost(symbol):
    if symbol in trending_coins:
        return 5  # boost confidence by 5% if trending
    return 0
