from utils.logger import log

def fetch_news_sentiment(symbol):
    try:
        log("News sentiment fetching disabled temporarily", level='INFO')
        return {'score': 0.0, 'magnitude': 0.0}
    except Exception as e:
        log(f"Error fetching sentiment: {e}", level='ERROR')
        return None
