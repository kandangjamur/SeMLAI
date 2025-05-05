import pandas as pd
import numpy as np
from utils.logger import log

def find_support_resistance(df, window=20):
    """
    Find support and resistance levels using rolling min/max.
    """
    try:
        df = df.copy()
        df["support"] = df["low"].rolling(window=window, min_periods=1).min()
        df["resistance"] = df["high"].rolling(window=window, min_periods=1).max()
        return df
    except Exception as e:
        log(f"Error finding support/resistance: {e}", level='ERROR')
        return None

def detect_breakout(symbol, df):
    """
    Detect breakout above resistance or below support with volume confirmation.
    Returns: dict with breakout status and direction.
    """
    try:
        if len(df) < 20:
            log(f"[{symbol}] Insufficient data for breakout detection", level='WARNING')
            return {"is_breakout": False, "direction": None}

        df = find_support_resistance(df)
        if df is None:
            return {"is_breakout": False, "direction": None}

        current_price = df["close"].iloc[-1]
        current_volume = df["volume"].iloc[-1]
        resistance = df["resistance"].iloc[-1]
        support = df["support"].iloc[-1]
        volume_sma_5 = df["volume"].rolling(window=5).mean().iloc[-1]

        breakout_threshold = 0.002  # 0.2% above/below level
        volume_multiplier = 1.5  # Volume > 1.5 * SMA for confirmation

        result = {"is_breakout": False, "direction": None}

        if (
            current_price > resistance * (1 + breakout_threshold)
            and current_volume > volume_sma_5 * volume_multiplier
        ):
            result["is_breakout"] = True
            result["direction"] = "up"
            log(f"[{symbol}] Bullish breakout detected above {resistance:.4f}")
        elif (
            current_price < support * (1 - breakout_threshold)
            and current_volume > volume_sma_5 * volume_multiplier
        ):
            result["is_breakout"] = True
            result["direction"] = "down"
            log(f"[{symbol}] Bearish breakout detected below {support:.4f}")

        return result
    except Exception as e:
        log(f"[{symbol}] Error in breakout detection: {e}", level='ERROR')
        return {"is_breakout": False, "direction": None}
