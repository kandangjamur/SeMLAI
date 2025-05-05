import pandas as pd
import numpy as np
from utils.logger import log

def detect_sr_levels(df, window=20, prominence=0.01):
    try:
        if len(df) < window or df['close'].std() <= 0 or df['volume'].mean() < 100000:
            log("Insufficient data or low volume for SR detection", level='WARNING')
            return {"support": None, "resistance": None}

        df = df.copy()
        df["volume_sma_20"] = df["volume"].rolling(window=20).mean()

        # Identify pivot highs and lows
        highs = df["high"].rolling(window=window, center=True).max()
        lows = df["low"].rolling(window=window, center=True).min()
        
        pivot_highs = df[df["high"] == highs]
        pivot_lows = df[df["low"] == lows]

        # Filter pivots based on prominence and volume
        resistance_levels = []
        support_levels = []

        for idx, row in pivot_highs.iterrows():
            if row["volume"] > 1.5 * row["volume_sma_20"]:
                price = row["high"]
                if all(abs(price - r) > price * prominence for r in resistance_levels):
                    resistance_levels.append(price)

        for idx, row in pivot_lows.iterrows():
            if row["volume"] > 1.5 * row["volume_sma_20"]:
                price = row["low"]
                if all(abs(price - s) > price * prominence for s in support_levels):
                    support_levels.append(price)

        # Fake breakout detection
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        if len(df) >= 3:
            next_candle = df.iloc[-3]
            for r in resistance_levels:
                if prev["high"] > r and latest["close"] <= r and next_candle["close"] <= r:
                    log(f"Fake breakout detected at resistance {r}", level='WARNING')
                    return {"support": None, "resistance": None}
            for s in support_levels:
                if prev["low"] < s and latest["close"] >= s and next_candle["close"] >= s:
                    log(f"Fake breakout detected at support {s}", level='WARNING')
                    return {"support": None, "resistance": None}

        # Select closest valid levels
        current_price = latest["close"]
        support = min(support_levels, key=lambda x: abs(x - current_price)) if support_levels else None
        resistance = min(resistance_levels, key=lambda x: abs(x - current_price)) if resistance_levels else None

        # Zero value check
        if support is not None and support <= 0:
            support = None
        if resistance is not None and resistance <= 0:
            resistance = None

        return {"support": round(support, 4) if support else None, "resistance": round(resistance, 4) if resistance else None}

    except Exception as e:
        log(f"Error in detect_sr_levels: {e}", level='ERROR')
        return {"support": None, "resistance": None}
