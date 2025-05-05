import httpx
import cachetools
from utils.logger import log
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

sentiment_cache = cachetools.TTLCache(maxsize=100, ttl=900)  # 15-minute cache
analyzer = SentimentIntensityAnalyzer()

async def fetch_sentiment(symbol):
    try:
        if symbol in sentiment_cache:
            log(f"[{symbol}] Using cached sentiment")
            return sentiment_cache[symbol]

        # Placeholder: Fetch posts or news (use a free API or mock data)
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://api.example.com/news?symbol={symbol}", timeout=5)
            if response.status_code != 200:
                log(f"[{symbol}] Failed to fetch news: {response.text}", level='WARNING')
                return 0.5  # Neutral sentiment

        texts = response.json().get("texts", [])
        if not texts:
            log(f"[{symbol}] No news texts found", level='WARNING')
            return 0.5

        scores = [analyzer.polarity_scores(text)["compound"] for text in texts]
        avg_score = sum(scores) / len(scores) if scores else 0.5
        sentiment_cache[symbol] = avg_score
        log(f"[{symbol}] Sentiment score: {avg_score}")
        return avg_score
    except Exception as e:
        log(f"[{symbol}] Error fetching sentiment: {e}", level='ERROR')
        return 0.5  # Neutral sentiment

def adjust_confidence(symbol, confidence, sentiment_score):
    try:
        if sentiment_score < 0.2:  # Negative sentiment
            log(f"[{symbol}] Negative sentiment detected, reducing confidence", level='WARNING')
            return max(0, confidence - 5)
        elif sentiment_score > 0.6:  # Positive sentiment
            return min(95, confidence + 5)
        return confidence
    except Exception as e:
        log(f"[{symbol}] Error adjusting confidence: {e}", level='ERROR')
        return confidence
