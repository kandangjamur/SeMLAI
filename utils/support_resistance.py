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
        df['support'] = df['support'].fillna(df['low'].min())
        df['resistance'] = df['resistance'].fillna(df['high'].max())
        
        # Ensure no NaN remains
        if df['support'].isna().any() or df['resistance'].isna().any():
            log("NaN values still present in support/resistance after filling", level="WARNING")
            df['support'] = df['support'].fillna(df['low'].iloc[-1])
            df['resistance'] = df['resistance'].fillna(df['high'].iloc[-1])
        
        return df
    except Exception as e:
        log(f"Error in support/resistance calculation: {e}", level="ERROR")
        return df

def detect_breakout(symbol, df):
    try:
        if len(df) < 3:
            return {"is_breakout": False, "direction": "none"}
        
        current_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        support = df['support'].iloc[-1]
        resistance = df['resistance'].iloc[-1]
        
        if pd.isna(support) or pd.isna(resistance):
            log(f"[{symbol}] Invalid support/resistance values", level="WARNING")
            return {"is_breakout": False, "direction": "none"}
        
        if prev_price <= resistance and current_price > resistance:
            return {"is_breakout": True, "direction": "up"}
        elif prev_price >= support and current_price < support:
            return {"is_breakout": True, "direction": "down"}
        else:
            return {"is_breakout": False, "direction": "none"}
    except Exception as e:
        log(f"Error detecting breakout for {symbol}: {e}", level="ERROR")
        return {"is_breakout": False, "direction": "none"}
