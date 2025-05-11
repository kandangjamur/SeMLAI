import pandas as pd
import numpy as np
from utils.logger import log

def calculate_support_resistance(df, window=20, pivot_window=5):
    """
    Advanced support/resistance calculation using pivot points and rolling window.
    Parameters:
        df: DataFrame with OHLC data
        window: Rolling window for support/resistance
        pivot_window: Window for pivot point detection
    Returns:
        support, resistance: Calculated levels
    """
    try:
        df = df.copy()
        
        # Rolling support/resistance
        df['rolling_low'] = df['low'].rolling(window=window).min()
        df['rolling_high'] = df['high'].rolling(window=window).max()
        
        # Pivot point calculation
        df['pivot'] = (df['high'] + df['low'] + df['close']) / 3
        df['pivot_high'] = df['pivot'].rolling(window=pivot_window).max()
        df['pivot_low'] = df['pivot'].rolling(window=pivot_window).min()
        
        # Combine rolling and pivot-based levels
        support = min(df['rolling_low'].iloc[-1], df['pivot_low'].iloc[-1])
        resistance = max(df['rolling_high'].iloc[-1], df['pivot_high'].iloc[-1])
        
        if pd.isna(support) or pd.isna(resistance):
            log("NaN values in support/resistance calculation", level="WARNING")
            return None, None
        
        # Validate levels
        current_price = df['close'].iloc[-1]
        if abs(support - current_price) < 0.01 * current_price or abs(resistance - current_price) < 0.01 * current_price:
            log("Support/Resistance too close to current price", level="WARNING")
            return None, None
        
        log(f"Support/Resistance calculated: Last support={support:.2f}, resistance={resistance:.2f}", level="INFO")
        return support, resistance
    except Exception as e:
        log(f"Error calculating support/resistance: {str(e)}", level="ERROR")
        return None, None
