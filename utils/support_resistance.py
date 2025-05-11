import pandas as pd
import numpy as np
from utils.logger import log

def find_support_resistance(df, window=20, pivot_window=5):
    """
    Advanced support/resistance calculation using pivot points and rolling window.
    Parameters:
        df: DataFrame with OHLC data
        window: Rolling window for support/resistance
        pivot_window: Window for pivot point detection
    Returns:
        df: DataFrame with support and resistance columns
    """
    try:
        df = df.copy()
        
        # Rolling support/resistance
        df['rolling_low'] = df['low'].rolling(window=window).min()
        df['rolling_high'] = df['high'].rolling(window=window).max()
        
        # Pivot point calculation
        df['pivot'] = (df['high'] + df['low'] + df['close']) / 3
        df['pivot_low'] = df['pivot'].rolling(window=pivot_window).min()
        df['pivot_high'] = df['pivot'].rolling(window=pivot_window).max()
        
        # Assign support and resistance
        df['support'] = df[['rolling_low', 'pivot_low']].min(axis=1).astype('float32')
        df['resistance'] = df[['rolling_high', 'pivot_high']].max(axis=1).astype('float32')
        
        if df['support'].isna().any() or df['resistance'].isna().any():
            log("NaN values in support/resistance calculation", level="WARNING")
            df['support'].fillna(df['low'], inplace=True)
            df['resistance'].fillna(df['high'], inplace=True)
        
        # Validate levels
        current_price = df['close'].iloc[-1]
        if abs(df['support'].iloc[-1] - current_price) < 0.01 * current_price or \
           abs(df['resistance'].iloc[-1] - current_price) < 0.01 * current_price:
            log("Support/Resistance too close to current price", level="WARNING")
            df['support'].iloc[-1] = df['low'].iloc[-1]
            df['resistance'].iloc[-1] = df['high'].iloc[-1]
        
        log(f"Support/Resistance calculated: Last support={df['support'].iloc[-1]:.2f}, resistance={df['resistance'].iloc[-1]:.2f}", level="INFO")
        return df
    except Exception as e:
        log(f"Error calculating support/resistance: {str(e)}", level="ERROR")
        return None

def detect_breakout(symbol, df):
    """
    Detect breakout above resistance or below support.
    Parameters:
        symbol: Trading pair
        df: DataFrame with OHLC and support/resistance
    Returns:
        dict: Breakout information
    """
    try:
        if df is None or len(df) < 2:
            log(f"[{symbol}] Insufficient data for breakout detection", level="WARNING")
            return {"is_breakout": False, "direction": None}
        
        current_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        support = df['support'].iloc[-1]
        resistance = df['resistance'].iloc[-1]
        
        # Breakout conditions
        if prev_price <= resistance and current_price > resistance:
            log(f"[{symbol}] Breakout detected: Upward through resistance {resistance:.2f}", level="INFO")
            return {"is_breakout": True, "direction": "up"}
        elif prev_price >= support and current_price < support:
            log(f"[{symbol}] Breakout detected: Downward through support {support:.2f}", level="INFO")
            return {"is_breakout": True, "direction": "down"}
        else:
            return {"is_breakout": False, "direction": None}
    except Exception as e:
        log(f"[{symbol}] Error detecting breakout: {str(e)}", level="ERROR")
        return {"is_breakout": False, "direction": None}
