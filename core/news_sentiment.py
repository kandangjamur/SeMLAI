import os
import requests
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("NEWS_API_KEY")

def get_sentiment_boost(symbol):
    try:
        query = symbol.split('/')[0]
        url = f"https://newsapi.org/v2/everything?q={query}&apiKey={API_KEY}"
        response = requests.get(url)
        if response.status_code == 200 and 'articles' in response.json():
            articles = response.json()['articles']
            if len(articles) > 2:
                return 5
        return 0
    except:
        return 0
