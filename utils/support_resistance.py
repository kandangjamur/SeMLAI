import pandas as pd
import numpy as np

def find_support_resistance(df):
    try:
        df = df.copy()
        window = 5
        df['support'] = df['low'].rolling(window=window, center=True).min()
        df['resistance'] = df['high'].rolling(window=window, center=True).max()
        
        # Fill NaN values with nearest available values
        df['support'] = df['support'].ffill().bfill()
        df['resistance'] = df['resistance'].ffill().bfill()
        
        # If still NaN, use min and max of the entire series
        if df['support'].isna().any():
            df['support'] = df['low'].min()
        if df['resistance'].isna().any():
            df['resistance'] = df['high'].max()
        
        return df
    except Exception as e:
        print(f"Error in support/resistance calculation: {e}")
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
            return {"is_breakout": False, "direction": "none"}
        
        if prev_price <= resistance and current_price > resistance:
            return {"is_breakout": True, "direction": "up"}
        elif prev_price >= support and current_price < support:
            return {"is_breakout": True, "direction": "down"}
        else:
            return {"is_breakout": False, "direction": "none"}
    except Exception as e:
        print(f"Error detecting breakout for {symbol}: {e}")
        return {"is_breakout": False, "direction": "none"}
