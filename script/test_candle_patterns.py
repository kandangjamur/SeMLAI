from model.predictor import SignalPredictor
from core.ml_prediction import get_ml_prediction
from core.candle_patterns import (
    is_bullish_engulfing, is_bearish_engulfing, is_doji,
    is_hammer, is_shooting_star, is_three_white_soldiers,
    is_three_black_crows
)
import sys
import os
import asyncio
import pandas as pd
import numpy as np
import ccxt
import logging
from datetime import datetime

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger()

# Import modules


async def calculate_indicators(df):
    """Calculate indicators for testing"""
    predictor = SignalPredictor()
    return await predictor.calculate_indicators(df)


async def test_candlestick_patterns():
    """Test candlestick pattern recognition and ML prediction"""
    try:
        logger.info("Testing candlestick pattern recognition...")

        # Initialize exchange
        exchange = ccxt.binance({
            'enableRateLimit': True
        })

        # Test with some symbols
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        timeframe = '1h'

        for symbol in symbols:
            logger.info(f"\nAnalyzing {symbol} for candlestick patterns...")

            # Fetch OHLCV data
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=100)
            df = pd.DataFrame(
                ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            # Calculate indicators
            df = await calculate_indicators(df)

            # Find patterns in the data
            logger.info("Checking for patterns in most recent candles:")

            # Calculate patterns for the last 5 candles
            for i in range(min(5, len(df))):
                idx = len(df) - i - 1
                candle_time = df['timestamp'].iloc[idx]
                close_price = df['close'].iloc[idx]

                logger.info(
                    f"\nCandle {idx} ({candle_time}), Close: {close_price}")

                # Check each pattern
                subset = df.iloc[:idx+1]
                if len(subset) > 1:  # Need at least 2 candles for engulfing patterns
                    if is_bullish_engulfing(subset).iloc[-1]:
                        logger.info("✅ Bullish Engulfing pattern detected")

                    if is_bearish_engulfing(subset).iloc[-1]:
                        logger.info("✅ Bearish Engulfing pattern detected")

                if is_doji(subset).iloc[-1]:
                    logger.info("✅ Doji pattern detected")

                if is_hammer(subset).iloc[-1]:
                    logger.info("✅ Hammer pattern detected")

                if is_shooting_star(subset).iloc[-1]:
                    logger.info("✅ Shooting Star pattern detected")

                if len(subset) > 3:  # Need at least 4 candles for three candle patterns
                    if is_three_white_soldiers(subset).iloc[-1]:
                        logger.info("✅ Three White Soldiers pattern detected")

                    if is_three_black_crows(subset).iloc[-1]:
                        logger.info("✅ Three Black Crows pattern detected")

            # Test ML prediction with patterns
            logger.info("\nTesting ML prediction with candlestick patterns...")
            ml_result = get_ml_prediction(symbol, df)

            logger.info(f"ML Prediction: {ml_result.get('direction')}")
            logger.info(f"Confidence: {ml_result.get('confidence'):.2f}%")
            logger.info(f"Source: {ml_result.get('source')}")

            # Check if any patterns were detected
            patterns = ml_result.get('patterns', [])
            if patterns:
                logger.info(f"Detected patterns: {', '.join(patterns)}")
            else:
                logger.info("No candlestick patterns detected.")

            # Wait a bit to avoid rate limiting
            await asyncio.sleep(1)

        logger.info("\nCandlestick pattern test completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Error testing candlestick patterns: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("Starting candlestick pattern test")

    # Run the test
    asyncio.run(test_candlestick_patterns())
