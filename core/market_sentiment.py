import requests
import os
import logging
from datetime import datetime, timedelta
import json
import traceback

# Get logger
logger = logging.getLogger("crypto-signal-bot")
if not logger.handlers:
    logger = logging.getLogger()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[logging.StreamHandler()]
    )


class MarketSentimentAnalyzer:
    """Analyzes market sentiment using the Fear & Greed Index"""

    def __init__(self):
        self.cache = {}
        self.cache_expiry = 3600  # Cache expiry in seconds (1 hour)
        self.data_dir = os.path.join(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))), "data")
        self.cache_file = os.path.join(self.data_dir, "fear_greed_cache.json")
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """Make sure the data directory exists"""
        os.makedirs(self.data_dir, exist_ok=True)

    def _load_cache(self):
        """Load cached Fear & Greed data if available"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    # Check if cache is still valid (less than 1 hour old)
                    if datetime.now().timestamp() - data.get('timestamp', 0) < self.cache_expiry:
                        logger.debug("Using cached Fear & Greed data")
                        return data.get('data')
        except Exception as e:
            logger.error(f"Error loading Fear & Greed cache: {str(e)}")
        return None

    def _save_cache(self, data):
        """Save Fear & Greed data to cache"""
        try:
            cache_data = {
                'timestamp': datetime.now().timestamp(),
                'data': data
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            logger.error(f"Error saving Fear & Greed cache: {str(e)}")

    def get_fear_greed_index(self):
        """
        Get the Fear & Greed Index from alternative.me API
        Returns:
            dict: Fear & Greed Index data with value and classification
        """
        # Check cache first
        cached_data = self._load_cache()
        if cached_data:
            return cached_data

        try:
            # Make API request
            url = "https://api.alternative.me/fng/?limit=2"
            logger.info(f"Fetching Fear & Greed Index from {url}")

            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                logger.error(
                    f"Failed to get Fear & Greed Index: {response.status_code} - {response.text}")
                return self._get_default_sentiment()

            data = response.json()

            if 'data' not in data or not data['data']:
                logger.error("No data in Fear & Greed Index response")
                return self._get_default_sentiment()

            # Get latest Fear & Greed Index data
            latest = data['data'][0]

            # Process the data
            result = {
                'value': int(latest['value']),
                'value_classification': latest['value_classification'],
                'timestamp': datetime.fromtimestamp(int(latest['timestamp'])).strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'alternative.me'
            }

            # Add trend information if available
            if len(data['data']) > 1:
                yesterday = data['data'][1]
                value_change = int(latest['value']) - int(yesterday['value'])
                result['trend'] = value_change
                result['trend_direction'] = 'up' if value_change > 0 else 'down' if value_change < 0 else 'stable'
                logger.info(
                    f"Fear & Greed Index: {result['value']} ({result['value_classification']}) Trend: {result['trend_direction']}")
            else:
                logger.info(
                    f"Fear & Greed Index: {result['value']} ({result['value_classification']})")

            # Cache the result
            self._save_cache(result)

            return result

        except Exception as e:
            logger.error(f"Error getting Fear & Greed Index: {str(e)}")
            logger.error(traceback.format_exc())
            return self._get_default_sentiment()

    def _get_default_sentiment(self):
        """Return default sentiment in case of API failure"""
        return {
            'value': 50,
            'value_classification': 'neutral',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source': 'default',
            'error': 'Failed to fetch real data'
        }

    def adjust_confidence_with_market_sentiment(self, confidence, direction=None, symbol=None):
        """
        Adjust confidence based on market sentiment (Fear & Greed Index)

        Args:
            confidence (float): Base confidence score
            direction (str): Trading direction ('LONG' or 'SHORT')
            symbol (str): Symbol for logging

        Returns:
            float: Adjusted confidence
        """
        try:
            # Get Fear & Greed Index
            fng = self.get_fear_greed_index()
            fng_value = fng['value']
            fng_class = fng['value_classification']

            # Base adjustment values
            adjustment = 0

            # 1. Extreme fear (0-25): Boost SHORT signals, reduce LONG signals
            # 2. Fear (26-45): Slight boost to SHORT signals
            # 3. Neutral (46-55): No adjustment
            # 4. Greed (56-75): Slight boost to LONG signals
            # 5. Extreme greed (76-100): Boost LONG signals, reduce SHORT signals

            if fng_value <= 25:  # Extreme fear
                if direction == 'SHORT':
                    # Higher adjustment for lower values
                    adjustment = 5.0 + (25 - fng_value) / 5
                    logger.info(
                        f"[{symbol}] 📉 Extreme fear ({fng_value}): boosting SHORT confidence by {adjustment:.2f}%")
                elif direction == 'LONG':
                    # Higher reduction for lower values
                    adjustment = -5.0 - (25 - fng_value) / 5
                    logger.info(
                        f"[{symbol}] 📉 Extreme fear ({fng_value}): reducing LONG confidence by {abs(adjustment):.2f}%")

            elif fng_value <= 45:  # Fear
                if direction == 'SHORT':
                    adjustment = 2.5
                    logger.info(
                        f"[{symbol}] 📉 Fear ({fng_value}): boosting SHORT confidence by {adjustment:.2f}%")
                elif direction == 'LONG':
                    adjustment = -2.5
                    logger.info(
                        f"[{symbol}] 📉 Fear ({fng_value}): reducing LONG confidence by {abs(adjustment):.2f}%")

            elif fng_value <= 55:  # Neutral
                logger.info(
                    f"[{symbol}] 📊 Neutral market sentiment ({fng_value}): no confidence adjustment")

            elif fng_value <= 75:  # Greed
                if direction == 'LONG':
                    adjustment = 2.5
                    logger.info(
                        f"[{symbol}] 📈 Greed ({fng_value}): boosting LONG confidence by {adjustment:.2f}%")
                elif direction == 'SHORT':
                    adjustment = -2.5
                    logger.info(
                        f"[{symbol}] 📈 Greed ({fng_value}): reducing SHORT confidence by {abs(adjustment):.2f}%")

            else:  # Extreme greed (76-100)
                if direction == 'LONG':
                    # Higher adjustment for higher values
                    adjustment = 5.0 + (fng_value - 75) / 5
                    logger.info(
                        f"[{symbol}] 📈 Extreme greed ({fng_value}): boosting LONG confidence by {adjustment:.2f}%")
                elif direction == 'SHORT':
                    # Higher reduction for higher values
                    adjustment = -5.0 - (fng_value - 75) / 5
                    logger.info(
                        f"[{symbol}] 📈 Extreme greed ({fng_value}): reducing SHORT confidence by {abs(adjustment):.2f}%")

            # Apply adjustment
            adjusted_confidence = confidence + adjustment

            # Ensure confidence stays within valid bounds (50-98)
            adjusted_confidence = max(min(adjusted_confidence, 98.0), 50.0)

            return adjusted_confidence

        except Exception as e:
            logger.error(
                f"[{symbol}] Error adjusting confidence with market sentiment: {str(e)}")
            logger.error(traceback.format_exc())
            return confidence


# Create global instance for easy access
sentiment_analyzer = MarketSentimentAnalyzer()

# Convenience functions


def get_fear_greed_index():
    """Get Fear & Greed Index from global instance"""
    return sentiment_analyzer.get_fear_greed_index()


def adjust_confidence(confidence, direction=None, symbol=None):
    """Adjust confidence based on market sentiment from global instance"""
    return sentiment_analyzer.adjust_confidence_with_market_sentiment(confidence, direction, symbol)


if __name__ == "__main__":
    # Test the Fear & Greed Index functionality
    print("Testing Fear & Greed Index...")
    index_data = get_fear_greed_index()
    print(
        f"Current Fear & Greed Index: {index_data['value']} - {index_data['value_classification']}")

    # Test confidence adjustment
    test_confidences = [60, 75, 90]
    for conf in test_confidences:
        for direction in ['LONG', 'SHORT']:
            adjusted = adjust_confidence(conf, direction, "BTC/USDT")
            print(
                f"Original confidence: {conf}, Direction: {direction}, Adjusted: {adjusted}")

    print("Testing complete.")
