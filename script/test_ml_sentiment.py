from model.predictor import SignalPredictor
from core.ml_prediction import get_ml_prediction
from core.news_sentiment import fetch_sentiment, adjust_confidence
from core.whale_detector import detect_whale_activity
import os
import sys
import asyncio
import pandas as pd
import numpy as np
import ccxt
import random
from datetime import datetime
import logging

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
log = logging.getLogger("crypto-signal-bot")

# Import our modules


async def test_functionality():
    """Test ML prediction and sentiment analysis functionality"""
    log.info("Starting functionality test...")

    # Initialize predictor
    predictor = SignalPredictor()
    log.info("Initialized SignalPredictor")

    # Test symbols (mix of large and small cap)
    test_symbols = [
        "BTC/USDT", "ETH/USDT", "SOL/USDT",  # Large caps
        "DOGE/USDT", "ADA/USDT", "MATIC/USDT",  # Mid caps
        "AVAX/USDT", "LINK/USDT", "FIL/USDT"  # Small/mid caps
    ]

    # Random shuffle to avoid bias
    random.shuffle(test_symbols)
    test_symbols = test_symbols[:3]  # Just test 3 symbols to avoid rate limits

    # Initialize exchange
    exchange = ccxt.binance({
        'enableRateLimit': True
    })

    # Test results dictionary
    results = {
        "sentiment_analysis": [],
        "ml_prediction": [],
        "signals": []
    }

    for symbol in test_symbols:
        log.info(f"Testing {symbol}...")

        try:
            # Fetch OHLCV data
            ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=100)
            df = pd.DataFrame(
                ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            # Calculate indicators
            df_with_indicators = await predictor.calculate_indicators(df)

            # 1. Test sentiment analysis with direction
            sentiment_data = fetch_sentiment(symbol)
            log.info(
                f"Sentiment for {symbol}: {sentiment_data['sentiment_type']}, score={sentiment_data.get('score', 0):.2f}")

            # Test sentiment adjustment for both directions
            base_confidence = 70.0
            long_adjusted = adjust_confidence(
                base_confidence, sentiment_data, "LONG", symbol)
            short_adjusted = adjust_confidence(
                base_confidence, sentiment_data, "SHORT", symbol)

            # Log results
            log.info(
                f"LONG confidence after sentiment: {base_confidence:.2f} → {long_adjusted:.2f}")
            log.info(
                f"SHORT confidence after sentiment: {base_confidence:.2f} → {short_adjusted:.2f}")

            # Check if adjustment is correct (positive sentiment should boost LONG and reduce SHORT)
            if sentiment_data['sentiment_type'] == 'positive':
                log.info("Positive sentiment should boost LONG and reduce SHORT")
                if long_adjusted > base_confidence and short_adjusted < base_confidence:
                    log.info("✅ Sentiment adjustment working correctly")
                else:
                    log.warning(
                        "❌ Sentiment adjustment not working as expected!")
            elif sentiment_data['sentiment_type'] == 'negative':
                log.info("Negative sentiment should boost SHORT and reduce LONG")
                if short_adjusted > base_confidence and long_adjusted < base_confidence:
                    log.info("✅ Sentiment adjustment working correctly")
                else:
                    log.warning(
                        "❌ Sentiment adjustment not working as expected!")

            # 2. Test ML prediction
            ml_result = get_ml_prediction(symbol, df_with_indicators)
            log.info(
                f"ML prediction for {symbol}: {ml_result.get('direction')}, confidence={ml_result.get('confidence', 0):.2f}%")

            results["ml_prediction"].append({
                "symbol": symbol,
                "direction": ml_result.get('direction'),
                "confidence": ml_result.get('confidence', 0),
                "source": ml_result.get('source', 'unknown')
            })

            # 3. Test signal generation with sentiment and ML
            signal = await predictor.predict_signal(symbol, df_with_indicators, '1h')

            if signal:
                log.info(
                    f"Signal for {symbol}: {signal['direction']}, confidence={signal['confidence']}%, whale={signal['whale_activity']}, sentiment={signal['news_sentiment']}, ML={signal['ml_prediction']}")

                # Check if confidence is higher than it would be without ML and sentiment
                ml_effect = "matches" if signal['ml_prediction'] == signal['direction'] else "conflicts with"
                log.info(f"ML prediction {ml_effect} signal direction")

                # Check if ML boosted confidence
                if ml_effect == "matches" and signal['ml_confidence'] > 60:
                    log.info(
                        "ML prediction should boost confidence for this signal")

                results["signals"].append({
                    "symbol": symbol,
                    "direction": signal['direction'],
                    "confidence": signal['confidence'],
                    "whale_activity": signal['whale_activity'],
                    "sentiment": signal['news_sentiment'],
                    "ml_direction": signal['ml_prediction'],
                    "ml_confidence": signal['ml_confidence'],
                    "qualifies_for_telegram": signal['confidence'] >= 90.0
                })
            else:
                log.info(f"No signal generated for {symbol}")

            # Record sentiment for reporting
            results["sentiment_analysis"].append({
                "symbol": symbol,
                "sentiment_type": sentiment_data['sentiment_type'],
                "score": sentiment_data.get('score', 0),
                "long_confidence": long_adjusted,
                "short_confidence": short_adjusted
            })

            # Delay to prevent rate limiting
            await asyncio.sleep(1)

        except Exception as e:
            log.error(f"Error testing {symbol}: {str(e)}")

    # Summary of results
    log.info("\n--- TEST RESULTS SUMMARY ---")

    # Sentiment analysis results
    sentiment_types = {r["sentiment_type"]
                       for r in results["sentiment_analysis"]}
    log.info(
        f"Sentiment analysis: Found {len(sentiment_types)} different sentiment types")

    # ML prediction results
    ml_sources = {r["source"] for r in results["ml_prediction"]}
    log.info(f"ML prediction sources: {ml_sources}")

    # Signal generation results
    signals_generated = len(results["signals"])
    signals_for_telegram = sum(
        1 for s in results["signals"] if s["qualifies_for_telegram"])
    log.info(
        f"Generated {signals_generated} signals, {signals_for_telegram} qualified for Telegram (90%+ confidence)")

    log.info("Test completed!")

if __name__ == "__main__":
    asyncio.run(test_functionality())
