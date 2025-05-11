import pandas as pd
import numpy as np
from utils.logger import log

def find_support_resistance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate support and resistance levels based on recent price action.
    Returns DataFrame with 'support' and 'resistance' columns.
    """
    try:
        # Ensure required columns exist
        required_columns = ['high', 'low', 'close']
        if not all(col in df.columns for col in required_columns):
            log("Missing required columns for support/resistance calculation", level="ERROR")
            return df

        # Initialize support and resistance columns
        df = df.copy()  # Avoid modifying the original DataFrame
        df['support'] = np.nan
        df['resistance'] = np.nan

        # Calculate pivot points for support and resistance
        window = 5  # Lookback period for identifying pivots
        for i in range(window, len(df) - window):
            # Support: lowest low in the lookback period
            if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
                df.loc[df.index[i], 'support'] = df['low'].iloc[i]
            # Resistance: highest high in the lookback period
            if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
                df.loc[df.index[i], 'resistance'] = df['high'].iloc[i]

        # Forward fill NaN values and use last known low/high as fallback
        if df['support'].isna().any() or df['resistance'].isna().any():
            log("NaN values in support/resistance calculation", level="WARNING")
            df['support'] = df['support'].fillna(method='ffill').fillna(df['low'])
            df['resistance'] = df['resistance'].fillna(method='ffill').fillna(df['high'])

        # Ensure support/resistance are not too close to current price
        current_price = df['close'].iloc[-1]
        min_distance = df['atr'].iloc[-1] * 0.5 if 'atr' in df.columns else 0.01 * current_price
        if abs(df['support'].iloc[-1] - current_price) < min_distance or \
           abs(df['resistance'].iloc[-1] - current_price) < min_distance:
            log("Support/Resistance too close to current price", level="WARNING")
            df.loc[df.index[-1], 'support'] = df['low'].iloc[-1]
            df.loc[df.index[-1], 'resistance'] = df['high'].iloc[-1]

        log(f"Support/Resistance calculated: Last support={df['support'].iloc[-1]:.2f}, "
            f"resistance={df['resistance'].iloc[-1]:.2f}", level="INFO")
        return df

    except Exception as e:
        log(f"Error in support/resistance calculation: {str(e)}", level="ERROR")
        df['support'] = df['low']
        df['resistance'] = df['high']
        return df

def detect_breakout(symbol: str, df: pd.DataFrame) -> dict:
    """
    Detect breakout signals based on price action relative to support/resistance.
    Returns dict with breakout information.
    """
    try:
        if 'support' not in df.columns or 'resistance' not in df.columns:
            log(f"[{symbol}] No support/resistance data for breakout detection", level="WARNING")
            return {"is_breakout": False, "direction": None}

        current_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        resistance = df['resistance'].iloc[-1]
        support = df['support'].iloc[-1]

        # Define breakout thresholds
        breakout_threshold = df['atr'].iloc[-1] * 0.5 if 'atr' in df.columns else 0.01 * current_price

        # Detect breakout
        if prev_price <= resistance and current_price > resistance + breakout_threshold:
            log(f"[{symbol}] Breakout detected: Price broke above resistance", level="INFO")
            return {"is_breakout": True, "direction": "up"}
        elif prev_price >= support and current_price < support - breakout_threshold:
            log(f"[{symbol}] Breakout detected: Price broke below support", level="INFO")
            return {"is_breakout": True, "direction": "down"}
        else:
            return {"is_breakout": False, "direction": None}

    except Exception as e:
        log(f"[{symbol}] Error in breakout detection: {str(e)}", level="ERROR")
        return {"is_breakout": False, "direction": None}
