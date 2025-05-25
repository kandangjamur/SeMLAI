from dotenv import load_dotenv
import random
import time
import re
import json
from datetime import datetime, timedelta
import logging
import os
import requests

# Load environment variables
load_dotenv('config.env')
load_dotenv('.env')

# Get logger
logger = logging.getLogger("crypto-signal-bot")

# Get API key from environment variables
NEWS_API_KEY = os.getenv('NEWS_API_KEY', '')


class NewsSentimentAnalyzer:
    def __init__(self):
        self.api_key = NEWS_API_KEY
        self.memory_cache = {}  # In-memory cache
        self.cache_expiry = 4 * 3600  # Cache expiry in seconds (4 hours)
        # Market-wide cache expiry (8 hours)
        self.market_cache_expiry = 8 * 3600
        self.api_calls_today = 0
        self.api_calls_reset_time = datetime.now() + timedelta(days=1)
        self.market_sentiment_cache = None
        self.market_sentiment_timestamp = 0
        self.api_call_counter_file = os.path.join(
            "data", "news_api_counter.json")

        # Create data directory if needed
        os.makedirs("data", exist_ok=True)
        os.makedirs(os.path.join("data", "sentiment_cache"), exist_ok=True)

        # Load previous API counter
        self.load_api_counter()

        # High-priority symbols that get dedicated API calls
        self.priority_symbols = ["BTC/USDT", "ETH/USDT",
                                 "BNB/USDT", "SOL/USDT", "XRP/USDT"]

        # Keyword dictionaries for sentiment analysis
        self.positive_keywords = [
            'bullish', 'surge', 'soar', 'rally', 'gain', 'jump', 'recover',
            'upturn', 'breakthrough', 'upswing', 'boom', 'outperform', 'thrive',
            'positive', 'optimistic', 'upbeat', 'promising', 'strong', 'upward',
            'growth', 'strength', 'rising', 'adoption', 'partnership', 'integration'
        ]

        self.negative_keywords = [
            'bearish', 'crash', 'plunge', 'slump', 'fall', 'drop', 'decline',
            'downturn', 'tumble', 'collapse', 'selloff', 'underperform', 'struggle',
            'negative', 'pessimistic', 'downbeat', 'concerning', 'weak', 'downward',
            'loss', 'weakness', 'falling', 'regulatory', 'ban', 'hack', 'scam', 'fraud'
        ]

        # Crypto-specific mapping to improve search results
        self.coin_keywords = {
            'BTC': 'Bitcoin',
            'ETH': 'Ethereum',
            'SOL': 'Solana',
            'ADA': 'Cardano',
            'XRP': 'Ripple XRP',
            'DOGE': 'Dogecoin',
            'SHIB': 'Shiba Inu',
            'AVAX': 'Avalanche',
            'DOT': 'Polkadot',
            'MATIC': 'Polygon',
            'NEAR': 'NEAR Protocol',
            'LINK': 'Chainlink',
            'UNI': 'Uniswap',
            'ATOM': 'Cosmos',
            'ALGO': 'Algorand',
            'FIL': 'Filecoin',
            'MANA': 'Decentraland',
            'SAND': 'The Sandbox',
            'AXS': 'Axie Infinity',
            'HIVE': 'Hive Blockchain',
            'APE': 'ApeCoin',
            'PEPE': 'Pepe Coin',
            'FLOKI': 'Floki Inu',
            'FTT': 'FTX Token',
            'MKR': 'Maker',
            'LTC': 'Litecoin',
            'TRX': 'TRON',
            'HBAR': 'Hedera',
            'SNX': 'Synthetix',
            'VET': 'VeChain',
            'IMX': 'Immutable X',
            'ZEN': 'Horizen',
            'ALGO': 'Algorand'
        }

        # Top 20 crypto assets for market-wide sentiment
        self.top_crypto = ["Bitcoin", "Ethereum", "Tether", "BNB", "Solana", "XRP",
                           "Cardano", "Avalanche", "Dogecoin", "Polygon"]

        # Initialize market sentiment on startup
        self.update_market_sentiment()

    def load_api_counter(self):
        """Load API call counter from file"""
        try:
            if os.path.exists(self.api_call_counter_file):
                with open(self.api_call_counter_file, 'r') as f:
                    data = json.load(f)
                    self.api_calls_today = data.get('count', 0)
                    reset_time = data.get('reset_time', None)
                    if reset_time:
                        self.api_calls_reset_time = datetime.fromisoformat(
                            reset_time)

                    # If reset time has passed, reset the counter
                    if datetime.now() > self.api_calls_reset_time:
                        self.api_calls_today = 0
                        self.api_calls_reset_time = datetime.now() + timedelta(days=1)
                        self.save_api_counter()
                        logger.info("Reset NewsAPI call counter (new day)")
        except Exception as e:
            logger.error(f"Error loading API counter: {str(e)}")
            # Initialize with conservative values
            self.api_calls_today = 50  # Start with half capacity to be safe
            self.api_calls_reset_time = datetime.now() + timedelta(days=1)
            self.save_api_counter()

    def save_api_counter(self):
        """Save API call counter to file"""
        try:
            with open(self.api_call_counter_file, 'w') as f:
                json.dump({
                    'count': self.api_calls_today,
                    'reset_time': self.api_calls_reset_time.isoformat()
                }, f)
        except Exception as e:
            logger.error(f"Error saving API counter: {str(e)}")

    def increment_api_counter(self):
        """Increment API call counter and save"""
        self.api_calls_today += 1
        logger.info(f"NewsAPI calls today: {self.api_calls_today}/100")
        self.save_api_counter()

    def can_make_api_call(self, symbol=None):
        """Check if we can make an API call, considering limits and priorities"""
        # Reset counter if a new day has started
        if datetime.now() > self.api_calls_reset_time:
            self.api_calls_today = 0
            self.api_calls_reset_time = datetime.now() + timedelta(days=1)
            self.save_api_counter()
            logger.info("Reset NewsAPI call counter (new day)")
            return True

        # Reserve 20 calls for high-priority symbols
        if self.api_calls_today >= 80 and symbol not in self.priority_symbols:
            return False

        # Absolute limit is 95 calls (keep 5 for emergency)
        if self.api_calls_today >= 95:
            return False

        return True

    def get_cache_file_path(self, symbol, days):
        """Get path to cache file for a symbol"""
        symbol_safe = symbol.replace('/', '_')
        return os.path.join("data", "sentiment_cache", f"{symbol_safe}_{days}d.json")

    def load_cached_sentiment(self, symbol, days):
        """Load sentiment from disk cache"""
        try:
            cache_file = self.get_cache_file_path(symbol, days)
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                cache_time = data.get('cache_time', 0)

                # Check if cache is still valid
                if datetime.now().timestamp() - cache_time < self.cache_expiry:
                    logger.info(f"[{symbol}] Using cached sentiment from file")
                    return data.get('result')
        except Exception as e:
            logger.error(f"[{symbol}] Error loading sentiment cache: {str(e)}")
        return None

    def save_cached_sentiment(self, symbol, days, result):
        """Save sentiment to disk cache"""
        try:
            cache_file = self.get_cache_file_path(symbol, days)
            with open(cache_file, 'w') as f:
                json.dump({
                    'result': result,
                    'cache_time': datetime.now().timestamp()
                }, f)
        except Exception as e:
            logger.error(f"[{symbol}] Error saving sentiment cache: {str(e)}")

    def clean_text(self, text):
        """Clean and normalize text for sentiment analysis"""
        if not text:
            return ""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove special characters and extra whitespace
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text.lower()

    def get_search_term(self, symbol):
        """Convert trading pair to search term for news API"""
        if not symbol or '/' not in symbol:
            return "cryptocurrency"

        base_currency = symbol.split('/')[0]

        # Use mapping for better search results
        if base_currency in self.coin_keywords:
            return self.coin_keywords[base_currency]

        return base_currency

    def analyze_sentiment(self, text):
        """
        Simple rule-based sentiment analysis

        Args:
            text (str): Text to analyze

        Returns:
            dict: Sentiment score and magnitude
        """
        text = self.clean_text(text)

        # Count positive and negative keywords
        positive_count = sum(
            1 for keyword in self.positive_keywords if keyword in text)
        negative_count = sum(
            1 for keyword in self.negative_keywords if keyword in text)

        # Calculate sentiment score (-1 to 1)
        total_count = positive_count + negative_count
        if total_count == 0:
            score = 0
            magnitude = 0
        else:
            score = (positive_count - negative_count) / total_count
            # Normalize by text length
            magnitude = total_count / (len(text.split()) / 10)
            magnitude = min(magnitude, 1.0)  # Cap at 1.0

        # Determine sentiment type
        if score > 0.2:
            sentiment_type = "positive"
        elif score < -0.2:
            sentiment_type = "negative"
        else:
            sentiment_type = "neutral"

        return {
            'score': score,
            'magnitude': magnitude,
            'type': sentiment_type
        }

    def get_fear_greed_based_sentiment(self):
        """Get sentiment based on Fear & Greed Index when NewsAPI is unavailable"""
        try:
            # Make API request to alternative.me
            url = "https://api.alternative.me/fng/?limit=1"
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                return {
                    'score': 0,
                    'magnitude': 0.3,
                    'article_count': 0,
                    'sentiment_type': 'neutral',
                    'latest_headlines': [],
                    'source': 'FallbackNeutral'
                }

            data = response.json()
            if 'data' not in data or not data['data']:
                return {
                    'score': 0,
                    'magnitude': 0.3,
                    'article_count': 0,
                    'sentiment_type': 'neutral',
                    'latest_headlines': [],
                    'source': 'FallbackNeutral'
                }

            # Get fear & greed value (0-100)
            fng_value = int(data['data'][0]['value'])
            fng_classification = data['data'][0]['value_classification']

            # Convert to sentiment
            if fng_value >= 70:  # Greed/Extreme Greed
                sentiment_type = "positive"
                score = 0.6
                magnitude = 0.7
            elif fng_value <= 30:  # Fear/Extreme Fear
                sentiment_type = "negative"
                score = -0.6
                magnitude = 0.7
            else:  # Neutral
                sentiment_type = "neutral"
                score = 0
                magnitude = 0.3

            logger.info(
                f"Using Fear & Greed Index as sentiment source: {fng_value} - {fng_classification}")

            return {
                'score': score,
                'magnitude': magnitude,
                'article_count': 0,
                'sentiment_type': sentiment_type,
                'latest_headlines': [],
                'source': 'FearGreedIndex',
                'fear_greed_value': fng_value,
                'fear_greed_classification': fng_classification
            }

        except Exception as e:
            logger.error(f"Error getting Fear & Greed Index: {str(e)}")
            return {
                'score': 0,
                'magnitude': 0.3,
                'article_count': 0,
                'sentiment_type': 'neutral',
                'latest_headlines': [],
                'source': 'FallbackNeutral'
            }

    def update_market_sentiment(self):
        """Update market-wide sentiment for all cryptocurrencies"""
        try:
            # Check if we need to update (based on time)
            current_time = datetime.now().timestamp()
            if (self.market_sentiment_cache and
                    current_time - self.market_sentiment_timestamp < self.market_cache_expiry):
                logger.info("Using cached market-wide sentiment")
                return self.market_sentiment_cache

            # Check if we can make API call
            if not self.can_make_api_call():
                logger.warning(
                    "Cannot update market sentiment - API limit reached")
                if self.market_sentiment_cache:
                    return self.market_sentiment_cache
                return self.get_fear_greed_based_sentiment()

            # Choose 2 random cryptos from top list to vary our queries
            search_terms = random.sample(self.top_crypto, 2)
            search_query = f"({' OR '.join(search_terms)}) AND cryptocurrency"

            # Set from_date to get news from last 1 day
            from_date = (datetime.now() - timedelta(days=1)
                         ).strftime('%Y-%m-%d')

            # Make API request
            url = 'https://newsapi.org/v2/everything'
            params = {
                'q': search_query,
                'from': from_date,
                'sortBy': 'publishedAt',
                'language': 'en',
                'apiKey': self.api_key
            }

            logger.info(f"Fetching market-wide sentiment: {search_query}")
            response = requests.get(url, params=params)
            self.increment_api_counter()

            # Check for API errors
            if response.status_code != 200:
                logger.warning(
                    f"NewsAPI error: {response.status_code} - {response.text}")
                # Fallback to Fear & Greed Index
                self.market_sentiment_cache = self.get_fear_greed_based_sentiment()
                self.market_sentiment_timestamp = current_time
                return self.market_sentiment_cache

            data = response.json()
            articles = data.get('articles', [])
            article_count = len(articles)

            logger.info(
                f"Found {article_count} news articles for market sentiment")

            if article_count == 0:
                # Fallback to Fear & Greed Index
                self.market_sentiment_cache = self.get_fear_greed_based_sentiment()
                self.market_sentiment_timestamp = current_time
                return self.market_sentiment_cache

            # Analyze sentiment for each article
            total_score = 0
            total_magnitude = 0
            headlines = []
            article_sentiments = []

            for article in articles[:10]:  # Analyze up to 10 articles
                title = self.clean_text(article.get('title', ''))
                description = self.clean_text(article.get('description', ''))

                # Combined text for sentiment analysis
                combined_text = f"{title} {description}"

                # Get sentiment for this article
                sentiment = self.analyze_sentiment(combined_text)

                # Add to totals
                total_score += sentiment['score']
                total_magnitude += sentiment['magnitude']

                # Save headline and URL
                headline = article.get('title', '')
                url = article.get('url', '')
                published_at = article.get('publishedAt', '')

                if headline and url:
                    headlines.append({
                        'title': headline,
                        'url': url,
                        'publishedAt': published_at,
                        'sentiment': sentiment['type']
                    })

                article_sentiments.append(sentiment)

            # Calculate average sentiment
            avg_score = total_score / \
                len(article_sentiments) if article_sentiments else 0
            avg_magnitude = total_magnitude / \
                len(article_sentiments) if article_sentiments else 0

            # Determine overall sentiment
            if avg_score > 0.2 and avg_magnitude > 0.2:
                sentiment_type = "positive"
            elif avg_score < -0.2 and avg_magnitude > 0.2:
                sentiment_type = "negative"
            else:
                sentiment_type = "neutral"

            # Prepare result
            result = {
                'score': avg_score,
                'magnitude': avg_magnitude,
                'article_count': article_count,
                'sentiment_type': sentiment_type,
                'latest_headlines': headlines[:3],  # Top 3 latest headlines
                'source': 'NewsAPI',
                'market_wide': True
            }

            # Add context message
            if sentiment_type == "positive":
                logger.info(
                    f"📈 Positive market sentiment detected with score {avg_score:.2f}")
            elif sentiment_type == "negative":
                logger.info(
                    f"📉 Negative market sentiment detected with score {avg_score:.2f}")
            else:
                logger.info(
                    f"📊 Neutral market sentiment with score {avg_score:.2f}")

            # Update cache
            self.market_sentiment_cache = result
            self.market_sentiment_timestamp = current_time

            return result

        except Exception as e:
            logger.error(f"Error updating market sentiment: {str(e)}")
            # Fallback to Fear & Greed Index
            return self.get_fear_greed_based_sentiment()

    def fetch_sentiment(self, symbol, days=2):
        """
        Fetch news sentiment for a cryptocurrency

        Args:
            symbol (str): Trading pair (e.g., BTC/USDT)
            days (int): Number of days to look back

        Returns:
            dict: Sentiment analysis results
        """
        try:
            # Generate cache key
            cache_key = f"{symbol}_{days}"
            current_time = datetime.now().timestamp()

            # First check memory cache
            if cache_key in self.memory_cache:
                cached_result, cache_time = self.memory_cache[cache_key]
                # Return cached result if still valid
                if current_time - cache_time < self.cache_expiry:
                    logger.info(f"[{symbol}] Using in-memory sentiment cache")
                    return cached_result

            # Then check file cache
            cached_result = self.load_cached_sentiment(symbol, days)
            if cached_result:
                # Also update memory cache
                self.memory_cache[cache_key] = (cached_result, current_time)
                return cached_result

            # If we're API rate limited or low on quota,
            # use the market-wide sentiment instead of individual API calls
            if not self.can_make_api_call(symbol):
                logger.warning(
                    f"[{symbol}] Using market-wide sentiment due to API limit")

                # Get/update market sentiment
                market_sentiment = self.update_market_sentiment()

                # Create a copy for this symbol
                result = market_sentiment.copy()
                result['note'] = f"Using market-wide sentiment for {symbol} (API limit)"

                # Cache the result
                self.memory_cache[cache_key] = (result, current_time)
                self.save_cached_sentiment(symbol, days, result)

                return result

            # Prepare API request
            search_term = self.get_search_term(symbol)
            from_date = (datetime.now() - timedelta(days=days)
                         ).strftime('%Y-%m-%d')

            logger.info(f"[{symbol}] Fetching news for: {search_term}")

            # NewsAPI request
            url = 'https://newsapi.org/v2/everything'
            params = {
                'q': search_term,
                'from': from_date,
                'sortBy': 'publishedAt',
                'language': 'en',
                'apiKey': self.api_key
            }

            response = requests.get(url, params=params)

            # Increment the API counter regardless of response
            self.increment_api_counter()

            # Check for API errors
            if response.status_code != 200:
                logger.warning(
                    f"[{symbol}] NewsAPI error: {response.status_code} - {response.text}")

                # Use market sentiment as fallback
                logger.info(
                    f"[{symbol}] Using market-wide sentiment as fallback")
                market_sentiment = self.update_market_sentiment()

                # Add specific symbol info to the result
                result = market_sentiment.copy()
                result['note'] = f"API error for {symbol}, using market sentiment"

                # Cache the result
                self.memory_cache[cache_key] = (result, current_time)
                self.save_cached_sentiment(symbol, days, result)

                return result

            data = response.json()
            articles = data.get('articles', [])
            article_count = len(articles)

            logger.info(f"[{symbol}] Found {article_count} news articles")

            if article_count == 0:
                logger.info(
                    f"[{symbol}] No articles found, using market sentiment")
                market_sentiment = self.update_market_sentiment()

                # Add specific symbol info to the result
                result = market_sentiment.copy()
                result['note'] = f"No articles for {symbol}, using market sentiment"

                # Cache the result
                self.memory_cache[cache_key] = (result, current_time)
                self.save_cached_sentiment(symbol, days, result)

                return result

            # Analyze sentiment for each article
            total_score = 0
            total_magnitude = 0
            headlines = []
            article_sentiments = []

            for article in articles[:10]:  # Analyze up to 10 articles
                title = self.clean_text(article.get('title', ''))
                description = self.clean_text(article.get('description', ''))

                # Combined text for sentiment analysis
                combined_text = f"{title} {description}"

                # Get sentiment for this article
                sentiment = self.analyze_sentiment(combined_text)

                # Add to totals
                total_score += sentiment['score']
                total_magnitude += sentiment['magnitude']

                # Save headline and URL
                headline = article.get('title', '')
                url = article.get('url', '')
                published_at = article.get('publishedAt', '')

                if headline and url:
                    headlines.append({
                        'title': headline,
                        'url': url,
                        'publishedAt': published_at,
                        'sentiment': sentiment['type']
                    })

                article_sentiments.append(sentiment)

            # Calculate average sentiment
            avg_score = total_score / \
                len(article_sentiments) if article_sentiments else 0
            avg_magnitude = total_magnitude / \
                len(article_sentiments) if article_sentiments else 0

            # Determine overall sentiment
            if avg_score > 0.2 and avg_magnitude > 0.2:
                sentiment_type = "positive"
            elif avg_score < -0.2 and avg_magnitude > 0.2:
                sentiment_type = "negative"
            else:
                sentiment_type = "neutral"

            # Prepare result
            result = {
                'score': avg_score,
                'magnitude': avg_magnitude,
                'article_count': article_count,
                'sentiment_type': sentiment_type,
                'latest_headlines': headlines[:3],  # Top 3 latest headlines
                'source': 'NewsAPI'
            }

            # Add context message
            if sentiment_type == "positive":
                msg = f"Positive news sentiment detected for {symbol}"
                if avg_magnitude > 0.5:
                    msg += " with strong intensity"
                logger.info(f"[{symbol}] 📈 {msg}")
            elif sentiment_type == "negative":
                msg = f"Negative news sentiment detected for {symbol}"
                if avg_magnitude > 0.5:
                    msg += " with strong intensity"
                logger.info(f"[{symbol}] 📉 {msg}")
            else:
                logger.info(f"[{symbol}] Neutral news sentiment")

            # Cache the result
            self.memory_cache[cache_key] = (result, current_time)
            self.save_cached_sentiment(symbol, days, result)

            return result

        except Exception as e:
            logger.error(
                f"[{symbol}] Error in news sentiment analysis: {str(e)}")

            # Use market sentiment as fallback
            try:
                market_sentiment = self.update_market_sentiment()
                result = market_sentiment.copy()
                result['note'] = f"Error for {symbol}, using market sentiment"
                return result
            except:
                # Last resort fallback
                return {
                    'score': 0,
                    'magnitude': 0,
                    'article_count': 0,
                    'sentiment_type': 'neutral',
                    'latest_headlines': [],
                    'error': str(e)
                }

    def adjust_confidence_with_sentiment(self, confidence, sentiment_data, direction=None, symbol=None):
        """
        Adjust confidence based on sentiment analysis results

        Args:
            confidence (float): Base confidence score
            sentiment_data (dict): Sentiment analysis results
            direction (str): Trading direction ('LONG' or 'SHORT')
            symbol (str): Symbol for logging

        Returns:
            float: Adjusted confidence
        """
        try:
            # Default adjustment value
            adjustment = 0

            # Get sentiment type
            sentiment_type = sentiment_data.get('sentiment_type', 'neutral')
            score = sentiment_data.get('score', 0)
            magnitude = sentiment_data.get('magnitude', 0)

            if not direction:
                return confidence

            # Calculate adjustment based on sentiment
            if sentiment_type == 'positive':
                if direction == 'LONG':
                    # Boost confidence for LONG positions with positive sentiment
                    adjustment = 3 + abs(score) * 5  # 3-8% boost
                    logger.info(
                        f"[{symbol}] 📈 Positive sentiment: boosting LONG confidence by {adjustment:.2f}%")
                else:
                    # Reduce confidence for SHORT positions with positive sentiment
                    adjustment = -3 - abs(score) * 5  # 3-8% reduction
                    logger.info(
                        f"[{symbol}] 📈 Positive sentiment: reducing SHORT confidence by {abs(adjustment):.2f}%")

            elif sentiment_type == 'negative':
                if direction == 'SHORT':
                    # Boost confidence for SHORT positions with negative sentiment
                    adjustment = 3 + abs(score) * 5  # 3-8% boost
                    logger.info(
                        f"[{symbol}] 📉 Negative sentiment: boosting SHORT confidence by {adjustment:.2f}%")
                else:
                    # Reduce confidence for LONG positions with negative sentiment
                    adjustment = -3 - abs(score) * 5  # 3-8% reduction
                    logger.info(
                        f"[{symbol}] 📉 Negative sentiment: reducing LONG confidence by {abs(adjustment):.2f}%")

            else:  # neutral
                if sentiment_data.get('source') == 'FearGreedIndex':
                    # If using Fear & Greed Index, we have special handling
                    fng_value = sentiment_data.get('fear_greed_value', 50)

                    if fng_value <= 25:  # Extreme fear - good for SHORT
                        if direction == 'SHORT':
                            adjustment = 4
                            logger.info(
                                f"[{symbol}] 😨 Extreme Fear: boosting SHORT confidence by {adjustment:.2f}%")
                        else:
                            adjustment = -4
                            logger.info(
                                f"[{symbol}] 😨 Extreme Fear: reducing LONG confidence by {abs(adjustment):.2f}%")

                    elif fng_value >= 75:  # Extreme greed - good for LONG
                        if direction == 'LONG':
                            adjustment = 4
                            logger.info(
                                f"[{symbol}] 🤑 Extreme Greed: boosting LONG confidence by {adjustment:.2f}%")
                        else:
                            adjustment = -4
                            logger.info(
                                f"[{symbol}] 🤑 Extreme Greed: reducing SHORT confidence by {abs(adjustment):.2f}%")
                else:
                    logger.info(
                        f"[{symbol}] Neutral sentiment: no confidence adjustment")

            # Apply adjustment with a smaller impact for market-wide sentiment
            if sentiment_data.get('market_wide', False):
                # Reduce impact of market-wide sentiment by 50%
                adjustment = adjustment * 0.5
                logger.info(
                    f"[{symbol}] Using market-wide sentiment, reduced adjustment to {adjustment:.2f}%")

            # Apply adjustment to confidence
            adjusted_confidence = confidence + adjustment

            # Ensure confidence stays within reasonable bounds
            adjusted_confidence = max(min(adjusted_confidence, 100.0), 50.0)

            return adjusted_confidence

        except Exception as e:
            logger.error(
                f"[{symbol}] Error adjusting confidence with sentiment: {str(e)}")
            return confidence


# Create a global instance
sentiment_analyzer = NewsSentimentAnalyzer()

# Convenience functions that use the global instance


def fetch_sentiment(symbol, days=2):
    """Wrapper for sentiment analyzer's fetch_sentiment method"""
    return sentiment_analyzer.fetch_sentiment(symbol, days)


def adjust_confidence(confidence, sentiment_data, direction=None, symbol=None):
    """Wrapper for sentiment analyzer's adjust_confidence method"""
    return sentiment_analyzer.adjust_confidence_with_sentiment(confidence, sentiment_data, direction, symbol)


# Test function
if __name__ == "__main__":
    # Simple test
    print("Testing news sentiment analysis...")
    for symbol in ["BTC/USDT", "ETH/USDT", "DOGE/USDT"]:
        sentiment = fetch_sentiment(symbol)
        print(
            f"Sentiment for {symbol}: {sentiment['sentiment_type']} (Score: {sentiment['score']:.2f})")

        # Test confidence adjustment
        base_confidence = 70.0
        for direction in ["LONG", "SHORT"]:
            adjusted = adjust_confidence(
                base_confidence, sentiment, direction, symbol)
            print(f"  {direction} confidence: {base_confidence} → {adjusted}")

    print("\nTesting market sentiment...")
    market_sentiment = sentiment_analyzer.update_market_sentiment()
    print(
        f"Market sentiment: {market_sentiment['sentiment_type']} (Score: {market_sentiment['score']:.2f})")

    print(f"\nAPI calls today: {sentiment_analyzer.api_calls_today}/100")
    print("Testing complete!")
