import pandas as pd
import numpy as np
from utils.logger import log

def find_support_resistance(df):
    try:
        df = df.copy()
        window = 5
        # Validate input data
        if df.empty or len(df) < window:
            log("Input DataFrame is empty or too small for support/resistance", level="ERROR")
            df['support'] = df['low']
            df['resistance'] = df['high']
            return df
        
        # Calculate support and resistance
        df['support'] = df['low'].rolling(window=window, min_periods=1).min()
        df['resistance'] = df['high'].rolling(window=window, min_periods=1).max()
        
        # Simplified NaN handling
        df['support'] = df['support'].fillna(df['low'])
        df['resistance'] = df['resistance'].fillna(df['high'])
        
        # Log final values
        log(f"Support/Resistance calculated: Last support={df['support'].iloc[-1]:.2f}, resistance={df['resistance'].iloc[-1]:.2f}")
        return df
    except Exception as e:
        log(f"Error in support/resistance calculation: {e}", level="ERROR")
        df['support'] = df['low']
        df['resistance'] = df['high']
        return df

def detect_breakout(symbol, df):
    try:
        if len(df) < 3:
            log(f"[{symbol}] Insufficient data for breakout detection", level="WARNING")
            return {"is_breakout": False, "direction": "none"}
        
        current_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        support = df['support'].iloc[-1]
        resistance = df['resistance'].iloc[-1]
        
        # Validate values
        if any(pd.isna(x) for x in [current_price, prev_price, support, resistance]):
            log(f"[{symbol}] Invalid values: support={support}, resistance={resistance}, current_price={current_price}, prev_price={prev_price}", level="WARNING")
            return {"is_breakout": False, "direction": "none"}
        
        if prev_price <= resistance and current_price > resistance:
            log(f"[{symbol}] Breakout detected: Up (Price={current_price:.2f}, Resistance={resistance:.2f})")
            return {"is_breakout": True, "direction": "up"}
        elif prev_price >= support and current_price < support:
            log(f"[{symbol}] Breakout detected: Down (Price={current_price:.2f}, Support={support:.2f})")
            return {"is_breakout": True, "direction": "down"}
        else:
            return {"is_breakout": False, "direction": "none"}
    except Exception as e:
        log(f"Error detecting breakout for {symbol}: {e}", level="ERROR")
        return {"is_breakout": False, "direction": "none"}
