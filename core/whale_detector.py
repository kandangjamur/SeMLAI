import pandas as pd
import numpy as np
import logging
from datetime import datetime
import math

# Get logger
logger = logging.getLogger("crypto-signal-bot")


def detect_whale_activity(symbol, df):
    """
    Detect whale activity based on volume, price movement patterns and large transactions

    Args:
        symbol (str): Trading pair symbol
        df (pandas.DataFrame): OHLCV data

    Returns:
        dict: Whale activity details including score, type, and confidence
    """
    try:
        # Check for sufficient data
        if len(df) < 20:
            logger.warning(f"[{symbol}] Insufficient data for whale detection")
            return {
                'detected': False,
                'score': 0,
                'type': None,
                'confidence': 0
            }

        # Extract recent data
        recent_df = df.iloc[-20:]

        # Calculate volume metrics
        avg_volume = recent_df['volume'].mean()
        current_volume = recent_df['volume'].iloc[-1]
        volume_sma_5 = recent_df['volume'].rolling(window=5).mean().iloc[-1]

        # Calculate price movement
        recent_price_change = (
            recent_df['close'].iloc[-1] - recent_df['open'].iloc[-1]) / recent_df['open'].iloc[-1] * 100

        # Calculate volume/price change ratio (higher means more volume with less price movement)
        volume_price_ratio = abs(
            current_volume / (abs(recent_price_change) + 0.01))

        # Volume spikes with minimal price movement indicate whale accumulation/distribution
        volume_spike = current_volume > (2 * volume_sma_5)
        abnormal_volume = current_volume > (3 * avg_volume)
        minimal_price_move = abs(
            recent_price_change) < 1.0 and current_volume > avg_volume * 1.5

        # Whale activity score (0-100)
        whale_score = 0

        # Check for volume spike
        if volume_spike:
            whale_score += 30
            logger.info(
                f"[{symbol}] Volume spike detected: current {current_volume:.2f} > 2x SMA5 {volume_sma_5:.2f}")

        # Check for abnormal volume
        if abnormal_volume:
            whale_score += 30
            logger.info(
                f"[{symbol}] Abnormal volume detected: current {current_volume:.2f} > 3x avg {avg_volume:.2f}")

        # Check for accumulation pattern (high volume, small price movement)
        if minimal_price_move and current_volume > avg_volume * 1.5:
            whale_score += 40
            logger.info(
                f"[{symbol}] Accumulation pattern: high volume with minimal price movement")

        # Determine activity type
        activity_type = None
        if whale_score >= 30:
            if recent_price_change > 0:
                activity_type = "bullish_accumulation"
            else:
                activity_type = "bearish_distribution"

        # Result
        detected = whale_score >= 30  # 30% threshold for detection

        if detected:
            logger.info(
                f"[{symbol}] 🐋 Whale activity detected with score: {whale_score}%, type: {activity_type}")

        return {
            'detected': detected,
            'score': whale_score,  # Integer score 0-100
            'type': activity_type,
            # Ensure confidence doesn't exceed 100
            'confidence': min(whale_score, 100)
        }

    except Exception as e:
        logger.error(f"[{symbol}] Error in whale detection: {str(e)}")
        return {
            'detected': False,
            'score': 0,
            'type': None,
            'confidence': 0
        }
