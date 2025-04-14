import time
from utils.logger import log

def start_sentiment_stream():
    while True:
        log("📰 Sentiment feed running...")
        time.sleep(300)
