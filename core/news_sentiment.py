import threading
import time
from utils.logger import log

def start_sentiment_stream():
    def stream():
        while True:
            log("📰 News sentiment analysis running...")
            time.sleep(1800)  # ہر 30 منٹ بعد

    threading.Thread(target=stream).start()
