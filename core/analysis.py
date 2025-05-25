from typing import Dict, List, Optional
import pandas as pd
import numpy as np
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger("crypto-signal-bot")


async def analyze_symbol_multi_timeframe(exchange, symbol: str, timeframes: List[str], predictor, bars: int = 200) -> Optional[Dict]:
    """Analyze a symbol across multiple timeframes and generate signals"""
    logger.info(f"[{symbol}] Starting multi-timeframe analysis...")

    try:
        signals = []

        # Analyze each timeframe
        for timeframe in timeframes:
            try:
                # Fetch ohlcv data
                ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=bars)

                if not ohlcv or len(ohlcv) < 20:
                    logger.warning(
                        f"[{symbol}] Not enough data for {timeframe}")
                    continue

                # Convert to dataframe
                df = pd.DataFrame(
                    ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)

                logger.info(f"[{symbol}] Starting analysis on {timeframe}")

                # Get signal for this timeframe
                signal = await predictor.predict_signal(symbol, df, timeframe)
                if signal:
                    signals.append(signal)
                    logger.info(
                        f"[{symbol}] Found {signal['direction']} signal for {timeframe} with confidence {signal['confidence']}%")
                else:
                    logger.info(f"[{symbol}] No signal for {timeframe}")
            except Exception as e:
                logger.error(
                    f"[{symbol}] Error in analysis for {timeframe}: {str(e)}")
                continue

        # Check if we have any signals
        if not signals:
            logger.info(f"[{symbol}] No valid signals across any timeframe")
            return None

        # Calculate timeframe agreement (proportion of signals with same direction)
        directions = [s['direction'] for s in signals]
        majority_direction = max(set(directions), key=directions.count)
        aligned_signals = [
            s for s in signals if s['direction'] == majority_direction]
        timeframe_agreement = len(aligned_signals) / len(signals)

        # Require at least 67% agreement across timeframes (2 out of 3 or 3 out of 4)
        required_agreement = 0.67
        if timeframe_agreement < required_agreement:
            logger.info(
                f"[{symbol}] Not enough timeframe signals: {len(aligned_signals)}/{len(signals)}")
            return None

        # Get the best signal (highest confidence) with the majority direction
        best_signal = max(aligned_signals, key=lambda x: x['confidence'])

        # Adjust confidence based on timeframe agreement
        avg_confidence = np.mean([s['confidence'] for s in aligned_signals])

        # Bonus for more timeframes agreeing
        tf_count_bonus = min(len(aligned_signals) * 2, 10)
        final_confidence = min(avg_confidence + tf_count_bonus, 100)

        # Update the best signal with the adjusted confidence
        best_signal['confidence'] = round(final_confidence, 2)
        best_signal['timeframe_agreement'] = round(
            timeframe_agreement * 100, 1)
        best_signal['agreeing_timeframes'] = len(aligned_signals)
        best_signal['total_timeframes'] = len(signals)

        logger.info(
            f"[{symbol}] Final signal selected with adjusted confidence: {best_signal['confidence']:.2f}%, "
            f"Direction: {best_signal['direction']}, "
            f"Timeframe Agreement: {timeframe_agreement:.2f}"
        )

        return {"symbol": symbol, "signals": [best_signal]}
    except Exception as e:
        logger.error(f"[{symbol}] Error in multi-timeframe analysis: {str(e)}")
        return None
