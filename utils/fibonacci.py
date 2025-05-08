import pandas as pd
import numpy as np
from utils.logger import log

def calculate_fibonacci_levels(df):
    try:
        if len(df) < 2 or df['high'].std() <= 0 or df['low'].std() <= 0:
            log("Insufficient data for Fibonacci levels", level='WARNING')
            return None

        df = df.copy()
        df = df.astype({'high': 'float32', 'low': 'float32', 'close': 'float32'})
        
        # Ensure 'timestamp' is in datetime format
        if 'timestamp' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        
        # Get the max high and min low over the last 100 rows (or all if less)
        window = min(len(df), 100)
        max_high = df['high'].tail(window).max()
        min_low = df['low'].tail(window).min()
        
        if pd.isna(max_high) or pd.isna(min_low) or max_high <= min_low:
            log("Invalid high/low for Fibonacci levels", level='WARNING')
            return None

        # Calculate Fibonacci levels
        diff = max_high - min_low
        fib_levels = {
            '0.0': min_low,
            '0.236': min_low + 0.236 * diff,
            '0.382': min_low + 0.382 * diff,
            '0.5': min_low + 0.5 * diff,
            '0.618': min_low + 0.618 * diff,
            '0.786': min_low + 0.786 * diff,
            '1.0': max_high
        }

        # Add Fibonacci levels to DataFrame
        for level, value in fib_levels.items():
            df[f'fib_{level}'] = value

        if df.isna().any().any() or df.isin([np.inf, -np.inf]).any().any():
            log("NaN or Inf values in Fibonacci levels", level='WARNING')
            return None

        log(f"Fibonacci levels calculated for {len(df)} rows")
        return df
    except Exception as e:
        log(f"Error in calculate_fibonacci_levels: {e}", level='ERROR')
        return None
