import numpy as np
import pandas as pd

def detect_sr_levels(df):
    """
    Detects support and resistance levels from swing highs and lows.
    Returns a dictionary with 'support' and 'resistance' keys.
    """
    highs = df['high'].values
    lows = df['low'].values

    support = []
    resistance = []

    for i in range(2, len(df) - 2):
        if lows[i] < lows[i-1] and lows[i] < lows[i+1] and lows[i+1] < lows[i+2] and lows[i-1] < lows[i-2]:
            support.append(lows[i])
        if highs[i] > highs[i-1] and highs[i] > highs[i+1] and highs[i+1] > highs[i+2] and highs[i-1] > highs[i-2]:
            resistance.append(highs[i])

    support_level = round(np.median(support), 3) if support else None
    resistance_level = round(np.median(resistance), 3) if resistance else None
    midpoint = round((support_level + resistance_level) / 2, 3) if support_level and resistance_level else None

    return {"support": support_level, "resistance": resistance_level, "midpoint": midpoint}
