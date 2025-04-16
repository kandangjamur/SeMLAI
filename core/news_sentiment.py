# core/news_sentiment.py

import requests
from bs4 import BeautifulSoup

def fetch_trending_coins():
    try:
        url = "https://coinmarketcap.com/trending-cryptocurrencies/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)

        soup = BeautifulSoup(response.text, "html.parser")
        names = soup.select("tbody tr td:nth-of-type(3) a")
        trending = [name.text.strip().upper() + "/USDT" for name in names[:10]]

        print(f"[TRENDING] {trending}")
        return trending
    except Exception as e:
        print(f"[Trending Fetch Error] {e}")
        return []

def get_sentiment_boost(symbol):
    trending = fetch_trending_coins()
    if symbol.upper() in trending:
        print(f"[SENTIMENT BOOST] {symbol} is trending! +10 boost applied.")
        return 10
    return 0

def start_sentiment_stream():
    print("[Sentiment] Sentiment stream initialized.")
    # Ye function ab bas system ko init kar raha hai
    # Real-time news stream agar add karni ho to uska block alag milega
