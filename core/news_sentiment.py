from utils.logger import log

def fetch_sentiment(symbol):
    try:
        # Temporary dummy sentiment data due to News API rate limit
        log(f"Fetching dummy sentiment for {symbol} (News API rate limit exceeded)", level='INFO')
        return {'score': 0.0, 'magnitude': 0.0}
    except Exception as e:
        log(f"Unexpected error in fetch_sentiment for {symbol}: {e}", level='ERROR')
        return None

def adjust_confidence(confidence, sentiment, *args):
    try:
        # Handle extra arguments gracefully
        if args:
            log(f"Extra arguments {args} ignored in adjust_confidence", level='WARNING')
        
        if sentiment is None or 'score' not in sentiment:
            log("No valid sentiment data for confidence adjustment", level='WARNING')
            return confidence

        sentiment_score = sentiment['score']
        if sentiment_score > 0.3:
            confidence *= 1.1  # Increase confidence by 10%
        elif sentiment_score < -0.3:
            confidence *= 0.9  # Decrease confidence by 10%

        return max(0.0, min(confidence, 100.0))
    except Exception as e:
        log(f"Error adjusting confidence: {e}", level='ERROR')
        return confidence
