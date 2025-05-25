import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import os
from datetime import datetime
import json
from utils.logger import logger


class ConfidenceManager:
    """
    Centralized management for signal confidence calculation and adjustment.
    Uses weighted indicators, market conditions, and historical performance.
    """

    def __init__(self):
        # Base weights for different technical indicators
        self.indicator_weights = {
            'rsi': 30,       # RSI has moderate importance
            'volume': 25,    # Volume has significant importance
            'macd': 35,      # MACD has high importance
            'price_action': 15,  # Price action patterns
            'trend': 25      # Trend direction
        }

        # Adjustments for different market conditions
        self.market_adjustments = {
            'high_volatility': -10,     # Reduce confidence in high volatility
            'low_volatility': -5,       # Slightly reduce in very low volatility
            'strong_trend': 15,         # Boost confidence in strong trends
            'sideways_market': -15,     # Reduce confidence in ranging markets
            'high_volume': 10,          # Boost for high volume
            'low_volume': -10           # Reduce for low volume
        }

        # Timeframe weights (higher timeframes get more weight)
        self.timeframe_weights = {
            '1m': 0.6,
            '5m': 0.7,
            '15m': 0.8,
            '30m': 0.9,
            '1h': 1.0,
            '4h': 1.1,
            '1d': 1.2
        }

        # Performance tracking
        self.performance_file = "logs/signal_performance.csv"
        self._ensure_performance_file()

        # Configuration paths
        self.config_path = "config/confidence_config.json"
        self._load_config()

        logger.info("Confidence Manager initialized")

    def _ensure_performance_file(self):
        """Create performance file if it doesn't exist"""
        if not os.path.exists(self.performance_file):
            os.makedirs(os.path.dirname(self.performance_file), exist_ok=True)
            df = pd.DataFrame(columns=[
                'symbol', 'direction', 'timeframe',
                'confidence', 'success', 'timestamp'
            ])
            df.to_csv(self.performance_file, index=False)

    def _load_config(self):
        """Load configuration if available"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)

                if 'indicator_weights' in config:
                    self.indicator_weights.update(config['indicator_weights'])
                if 'market_adjustments' in config:
                    self.market_adjustments.update(
                        config['market_adjustments'])
                if 'timeframe_weights' in config:
                    self.timeframe_weights.update(config['timeframe_weights'])

                logger.info("Loaded custom confidence configuration")
        except Exception as e:
            logger.warning(f"Could not load confidence config: {str(e)}")

    def calculate_weighted_confidence(self,
                                      symbol: str,
                                      df: pd.DataFrame,
                                      conditions: List[bool],
                                      condition_types: List[str],
                                      direction: str,
                                      timeframe: str) -> float:
        """
        Calculate confidence score with weighted indicators

        Args:
            symbol: Trading pair symbol
            df: OHLCV DataFrame with indicators
            conditions: List of boolean conditions
            condition_types: List of condition type names
            direction: 'LONG' or 'SHORT'
            timeframe: Timeframe string

        Returns:
            float: Confidence score 0-100
        """
        # Base confidence value
        base_confidence = 10

        # Calculate weighted sum from indicators
        weighted_sum = 0
        for condition, condition_type in zip(conditions, condition_types):
            if condition:
                if 'rsi' in condition_type.lower():
                    weighted_sum += self.indicator_weights['rsi']
                elif 'volume' in condition_type.lower():
                    weighted_sum += self.indicator_weights['volume']
                elif 'macd' in condition_type.lower():
                    weighted_sum += self.indicator_weights['macd']
                elif 'trend' in condition_type.lower():
                    weighted_sum += self.indicator_weights['trend']
                else:
                    weighted_sum += 20  # Default weight for other conditions

        # Calculate initial confidence score
        confidence = base_confidence + weighted_sum

        # Apply market context adjustments
        confidence = self.apply_market_adjustments(confidence, df, direction)

        # Apply timeframe weighting
        confidence = self.apply_timeframe_weighting(confidence, timeframe)

        # Apply historical performance adjustment
        confidence = self.apply_historical_adjustment(
            confidence, symbol, direction, timeframe)

        # Ensure confidence is within valid range
        confidence = min(max(confidence, 0), 100)

        logger.debug(
            f"[{symbol}] Calculated weighted confidence: {confidence:.2f}%")
        return confidence

    def apply_market_adjustments(self, confidence: float, df: pd.DataFrame, direction: str) -> float:
        """Apply adjustments based on current market conditions"""
        try:
            latest = df.iloc[-1]

            # Check for high volatility (using ATR)
            if 'atr' in df.columns:
                atr = latest['atr']
                atr_percent = (atr / latest['close']) * 100

                if atr_percent > 3.0:  # High volatility
                    confidence += self.market_adjustments['high_volatility']
                    logger.debug(
                        f"High volatility detected: ATR {atr_percent:.2f}%, adjusting confidence by {self.market_adjustments['high_volatility']}")
                elif atr_percent < 0.5:  # Very low volatility
                    confidence += self.market_adjustments['low_volatility']
                    logger.debug(
                        f"Low volatility detected: ATR {atr_percent:.2f}%, adjusting confidence by {self.market_adjustments['low_volatility']}")

            # Check for trend strength
            if all(col in df.columns for col in ['ema_20', 'ema_50']):
                ema_20 = df['ema_20'].iloc[-5:].values
                ema_50 = df['ema_50'].iloc[-5:].values

                # Detect strong trend - consecutive increasing/decreasing EMAs
                if direction == 'LONG' and all(ema_20[i] > ema_20[i-1] for i in range(1, len(ema_20))):
                    confidence += self.market_adjustments['strong_trend']
                    logger.debug(
                        f"Strong uptrend detected, adjusting confidence by {self.market_adjustments['strong_trend']}")
                elif direction == 'SHORT' and all(ema_20[i] < ema_20[i-1] for i in range(1, len(ema_20))):
                    confidence += self.market_adjustments['strong_trend']
                    logger.debug(
                        f"Strong downtrend detected, adjusting confidence by {self.market_adjustments['strong_trend']}")

                # Detect sideways market - EMAs too close together
                ema_diff_pct = abs(
                    latest['ema_20'] - latest['ema_50']) / latest['ema_50']
                if ema_diff_pct < 0.005:  # EMAs within 0.5%
                    confidence += self.market_adjustments['sideways_market']
                    logger.debug(
                        f"Sideways market detected, adjusting confidence by {self.market_adjustments['sideways_market']}")

            # Check volume conditions
            if 'volume' in df.columns and 'volume_sma_20' in df.columns:
                vol_ratio = latest['volume'] / latest['volume_sma_20']

                if vol_ratio > 2.0:  # Volume significantly above average
                    confidence += self.market_adjustments['high_volume']
                    logger.debug(
                        f"High volume detected: {vol_ratio:.2f}x average, adjusting confidence by {self.market_adjustments['high_volume']}")
                elif vol_ratio < 0.5:  # Volume significantly below average
                    confidence += self.market_adjustments['low_volume']
                    logger.debug(
                        f"Low volume detected: {vol_ratio:.2f}x average, adjusting confidence by {self.market_adjustments['low_volume']}")

            return confidence
        except Exception as e:
            logger.error(f"Error in apply_market_adjustments: {str(e)}")
            return confidence

    def apply_timeframe_weighting(self, confidence: float, timeframe: str) -> float:
        """Apply adjustments based on timeframe"""
        try:
            weight = self.timeframe_weights.get(timeframe, 1.0)
            return confidence * weight
        except Exception as e:
            logger.error(f"Error in apply_timeframe_weighting: {str(e)}")
            return confidence

    def apply_historical_adjustment(self, confidence: float, symbol: str, direction: str, timeframe: str) -> float:
        """Adjust confidence based on historical performance"""
        try:
            if not os.path.exists(self.performance_file):
                return confidence

            df = pd.read_csv(self.performance_file)

            # Filter relevant historical data
            filtered = df[(df['symbol'] == symbol) &
                          (df['direction'] == direction) &
                          (df['timeframe'] == timeframe)]

            if len(filtered) >= 3:  # Need minimum data points
                success_rate = filtered['success'].mean()

                if success_rate > 0.7:  # Good historical performance
                    adjustment = 1.15  # Boost confidence
                    logger.debug(
                        f"[{symbol}] Good historical performance ({success_rate:.2f}), boosting confidence by 15%")
                elif success_rate < 0.3:  # Poor historical performance
                    adjustment = 0.85  # Reduce confidence
                    logger.debug(
                        f"[{symbol}] Poor historical performance ({success_rate:.2f}), reducing confidence by 15%")
                else:
                    adjustment = 1.0  # Neutral

                confidence = confidence * adjustment

            return confidence
        except Exception as e:
            logger.error(f"Error in apply_historical_adjustment: {str(e)}")
            return confidence

    def record_signal_result(self, signal: Dict, success: bool) -> None:
        """Record signal results to improve future predictions"""
        try:
            new_record = {
                'symbol': signal['symbol'],
                'direction': signal['direction'],
                'timeframe': signal['timeframe'],
                'confidence': signal['confidence'],
                'success': 1 if success else 0,
                'timestamp': datetime.now().isoformat()
            }

            # Append to CSV
            pd.DataFrame([new_record]).to_csv(
                self.performance_file,
                mode='a',
                header=False,
                index=False
            )

            logger.info(
                f"Recorded signal result for {signal['symbol']}: success={success}")

            # Periodically clean up old records (keep last 1000)
            if os.path.exists(self.performance_file):
                try:
                    df = pd.read_csv(self.performance_file)
                    if len(df) > 1000:
                        df = df.tail(1000)
                        df.to_csv(self.performance_file, index=False)
                except:
                    pass

        except Exception as e:
            logger.error(f"Error recording signal result: {str(e)}")

    def get_dynamic_threshold(self, symbol: str, timeframe: str) -> float:
        """Get dynamic confidence threshold based on market conditions and timeframe"""
        base_threshold = 70.0

        # Higher threshold for shorter timeframes
        if timeframe in ['1m', '5m']:
            base_threshold += 5.0
        elif timeframe in ['1d', '4h']:
            base_threshold -= 5.0

        # Adjust threshold based on symbol volatility class
        # This would require additional volatility classification logic

        return base_threshold
