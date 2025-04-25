import threading
import time
from utils.logger import log

def start_sentiment_stream():
    def stream():
        while True:
            # Placeholder for real sentiment/news integration
            log("📰 News sentiment analysis running...")
            time.sleep(1800)  # 30 min interval

    threading.Thread(target=stream).start()
