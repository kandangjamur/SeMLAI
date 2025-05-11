import logging
import pandas as pd
import numpy as np
from typing import Dict

def calculate_support_resistance(symbol: str, df: pd.DataFrame) -> Dict[str, float]:
    log = logging.getLogger("crypto-signal-bot")
    
    try:
        # Ensure required columns exist
        if not all(col in df.columns for col in ['high', 'low', 'close']):
            log.error(f"[{symbol}] Missing required columns in DataFrame")
            return {"support": 0.0, "resistance": 0.0}
        
        # Calculate pivot points
        pivot = (df['high'] + df['low'] + df['close']) / 3
        support = pivot - (df['high'] - df['low'])
        resistance = pivot + (df['high'] - df['low'])
        
        # Create DataFrame for support and resistance
        sr_df = pd.DataFrame({
            'pivot': pivot,
            'support': support,
            'resistance': resistance
        })
        
        # Identify significant support/resistance levels
        sr_df['is_support'] = (sr_df['support'] > sr_df['support'].shift(1)) & (sr_df['support'] > sr_df['support'].shift(-1))
        sr_df['is_resistance'] = (sr_df['resistance'] < sr_df['resistance'].shift(1)) & (sr_df['resistance'] < sr_df['resistance'].shift(-1))
        
        # Filter significant levels
        support_levels = sr_df[sr_df['is_support']]['support']
        resistance_levels = sr_df[sr_df['is_resistance']]['resistance']
        
        # Get latest valid support and resistance
        df['support'] = np.nan
        df['resistance'] = np.nan
        
        if not support_levels.empty:
            df['support'] = support_levels.reindex(df.index).ffill().bfill()
        if not resistance_levels.empty:
            df['resistance'] = resistance_levels.reindex(df.index).ffill().bfill()
        
        # Fill remaining NaN with last low/high
        if df['support'].isna().any() or df['resistance'].isna().any():
            log.warning(f"[{symbol}] NaN values in support/resistance calculation")
            df['support'] = df['support'].ffill().bfill().fillna(df['low'])
            df['resistance'] = df['resistance'].ffill().bfill().fillna(df['high'])
        
        # Get latest support and resistance
        current_price = df['close'].iloc[-1]
        last_support = df['support'].iloc[-1]
        last_resistance = df['resistance'].iloc[-1]
        
        # Validate support/resistance
        if abs(last_support - current_price) < 0.005 * current_price or abs(last_resistance - current_price) < 0.005 * current_price:
            log.warning(f"[{symbol}] Support/Resistance too close to current price")
            last_support = df['low'].iloc[-1]
            last_resistance = df['high'].iloc[-1]
        
        return {
            "support": float(last_support),
            "resistance": float(last_resistance)
        }
    
    except Exception as e:
        log.error(f"[{symbol}] Error calculating support/resistance: {str(e)}")
        return {"support": 0.0, "resistance": 0.0}

def detect_breakout(symbol: str, df: pd.DataFrame) -> Dict[str, bool]:
    log = logging.getLogger("crypto-signal-bot")
    
    try:
        current_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        resistance = calculate_support_resistance(symbol, df)['resistance']
        support = calculate_support_resistance(symbol, df)['support']
        
        breakout_threshold = 0.01 * current_price  # 1% of current price
        
        is_breakout = False
        direction = None
        
        if current_price > resistance and prev_price <= resistance:
            if current_price > resistance + breakout_threshold:
                is_breakout = True
                direction = "up"
                log.info(f"[{symbol}] Breakout detected: Price {current_price:.2f} broke above resistance {resistance:.2f}")
        
        elif current_price < support and prev_price >= support:
            if current_price < support - breakout_threshold:
                is_breakout = True
                direction = "down"
                log.info(f"[{symbol}] Breakout detected: Price {current_price:.2f} broke below support {support:.2f}")
        
        return {
            "is_breakout": is_breakout,
            "direction": direction
        }
    
    except Exception as e:
        log.error(f"[{symbol}] Error detecting breakout: {str(e)}")
        return {"is_breakout": False, "direction": None}
