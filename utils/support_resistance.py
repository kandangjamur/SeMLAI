import numpy as np
import pandas as pd

def detect_sr_levels(df):
    """
    Detect basic support and resistance levels based on swing highs and lows.
    Returns dict with 'support' and 'resistance' levels.
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

    if support:
        support_level = round(np.median(support), 3)
    else:
        support_level = None

    if resistance:
        resistance_level = round(np.median(resistance), 3)
    else:
        resistance_level = None

    return {
        "support": support_level,
        "resistance": resistance_level
    }
