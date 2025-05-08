import os
import requests
from utils.logger import log
from dotenv import load_dotenv

load_dotenv()

def fetch_sentiment(symbol):
    try:
        api_key = os.getenv('NEWS_API_KEY')
        if not api_key:
            log("NEWS_API_KEY not found in .env", level='ERROR')
            return None

        # Construct API URL for News API
        query = f"{symbol} cryptocurrency"
        url = (
            f"https://newsapi.org/v2/everything?"
            f"q={query}&language=en&sortBy=publishedAt&apiKey={api_key}"
        )

        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get('status') != 'ok' or not data.get('articles'):
            log(f"No articles found for {symbol}", level='WARNING')
            return {'score': 0.0, 'magnitude': 0.0}

        # Simple sentiment analysis (mocked for now, replace with actual NLP if needed)
        articles = data['articles'][:10]  # Limit to 10 articles
        total_score = 0.0
        count = 0
        for article in articles:
            title = article.get('title', '').lower()
            # Basic keyword-based sentiment (replace with NLP model like VADER for production)
            if 'bullish' in title or 'rise' in title or 'surge' in title:
                total_score += 0.5
            elif 'bearish' in title or 'drop' in title or 'crash' in title:
                total_score -= 0.5
            count += 1

        avg_score = total_score / max(count, 1)
        log(f"Sentiment score for {symbol}: {avg_score}", level='INFO')
        return {'score': avg_score, 'magnitude': count / 10.0}

    except requests.exceptions.RequestException as e:
        log(f"Error fetching sentiment for {symbol}: {e}", level='ERROR')
        return None
    except Exception as e:
        log(f"Unexpected error in fetch_sentiment for {symbol}: {e}", level='ERROR')
        return None

def adjust_confidence(confidence, sentiment):
    try:
        if sentiment is None or 'score' not in sentiment:
            log("No valid sentiment data for confidence adjustment", level='WARNING')
            return confidence

        sentiment_score = sentiment['score']
        # Adjust confidence based on sentiment score
        if sentiment_score > 0.3:
            confidence *= 1.1  # Increase confidence by 10% for positive sentiment
        elif sentiment_score < -0.3:
            confidence *= 0.9  # Decrease confidence by 10% for negative sentiment

        # Ensure confidence stays within 0-100%
        return max(0.0, min(confidence, 100.0))
    except Exception as e:
        log(f"Error adjusting confidence: {e}", level='ERROR')
        return confidence
