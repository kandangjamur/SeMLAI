from core.ml_prediction import get_ml_prediction
import os
import sys
import logging
import pandas as pd
import numpy as np
import ccxt
import joblib
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger()

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)


def calculate_indicators(df):
    """Calculate technical indicators for testing"""
    # Calculate RSI (14)
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # Calculate MACD (12, 26, 9)
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macdsignal'] = df['macd'].ewm(span=9, adjust=False).mean()

    # Calculate Bollinger Bands (20, 2)
    df['sma20'] = df['close'].rolling(window=20).mean()
    df['stddev'] = df['close'].rolling(window=20).std()
    df['upper_band'] = df['sma20'] + (df['stddev'] * 2)
    df['lower_band'] = df['sma20'] - (df['stddev'] * 2)

    # Calculate ATR (14)
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['atr'] = true_range.rolling(14).mean()

    # Volume indicators
    df['volume_sma20'] = df['volume'].rolling(window=20).mean()

    return df


def test_ml_model():
    """Test the ML prediction functionality"""
    try:
        # Check if model exists
        model_path = os.path.join('models', 'random_forest_model.joblib')
        if not os.path.exists(model_path):
            logger.warning(
                f"Model not found at {model_path}. Run train_ml_model.py first or feature mismatch will be resolved with heuristic.")

        # Fetch some test data
        exchange = ccxt.binance({
            'enableRateLimit': True
        })

        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']

        for symbol in symbols:
            logger.info(f"\nTesting ML prediction for {symbol}")

            # Fetch OHLCV data
            ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=100)
            df = pd.DataFrame(
                ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            # Calculate indicators
            df = calculate_indicators(df)

            # Drop NaN rows
            df = df.dropna()

            # Get ML prediction
            ml_result = get_ml_prediction(symbol, df)

            # Print result
            logger.info(f"Direction: {ml_result.get('direction')}")
            logger.info(f"Confidence: {ml_result.get('confidence', 0):.2f}%")
            logger.info(f"Source: {ml_result.get('source', 'unknown')}")

            # Check if source is model or heuristic
            if ml_result.get('source') == 'ml_model':
                logger.info("✅ Successfully used ML model for prediction")
            else:
                logger.info(
                    "⚠️ Used heuristic prediction (model issues or not found)")

            # Check confidence cap
            if ml_result.get('confidence', 0) > 100:
                logger.error("❌ Confidence exceeds 100%!")
            else:
                logger.info("✅ Confidence properly capped")

        return True

    except Exception as e:
        logger.error(f"Error testing ML model: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    logger.info("Testing ML model functionality...")
    success = test_ml_model()

    if success:
        logger.info("\nML model test completed")
    else:
        logger.error("\nML model test failed")
