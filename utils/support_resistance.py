import pandas as pd
import numpy as np
from utils.logger import log

def find_support_resistance(df):
    try:
        df = df.copy()
        window = 5
        # Calculate support and resistance
        df['support'] = df['low'].rolling(window=window, min_periods=1).min()
        df['resistance'] = df['high'].rolling(window=window, min_periods=1).max()
        
        # Robust NaN handling
        if df['support'].isna().any():
            df['support'] = df['support'].fillna(df['low'].min())
        if df['resistance'].isna().any():
            df['resistance'] = df['resistance'].fillna(df['high'].max())
        
        # Final check for NaN
        if df['support'].isna().any() or df['resistance'].isna().any():
            log("NaN values persist in support/resistance, using last known values", level="WARNING")
            df['support'] = df['support'].fillna(df['low'].iloc[-1])
            df['resistance'] = df['resistance'].fillna(df['high'].iloc[-1])
        
        log(f"Support/Resistance calculated: Last support={df['support'].iloc[-1]:.2f}, resistance={df['resistance'].iloc[-1]:.2f}")
        return df
    except Exception as e:
        log(f"Error in support/resistance calculation: {e}", level="ERROR")
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
        
        if pd.isna(support) or pd.isna(resistance):
            log(f"[{symbol}] Invalid support/resistance values: support={support}, resistance={resistance}", level="WARNING")
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
