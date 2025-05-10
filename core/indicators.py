import pandas as pd
import numpy as np
from utils.logger import log

def calculate_rsi(data, periods=14):
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=periods).mean()
    avg_loss = loss.rolling(window=periods).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line

def calculate_indicators(df: pd.DataFrame):
    try:
        if len(df) < 26:  # Minimum for MACD
            log("Insufficient data for indicators", level="WARNING")
            return None
            
        df = df.copy()
        
        # RSI
        df['rsi'] = calculate_rsi(df['close'], periods=14)
        
        # MACD
        df['macd'], df['macd_signal'] = calculate_macd(df['close'])
        
        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(window=14).mean()
        
        # Handle NaN and Inf values
        df['rsi'] = df['rsi'].replace([np.inf, -np.inf], np.nan).fillna(50.0)
        df['macd'] = df['macd'].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        df['macd_signal'] = df['macd_signal'].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        df['atr'] = df['atr'].replace([np.inf, -np.inf], np.nan).fillna(df['atr'].mean())
        
        if df[['rsi', 'macd', 'macd_signal', 'atr']].isna().any().any():
            log("NaN values detected after handling", level="WARNING")
            return None
            
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'rsi', 'macd', 'macd_signal', 'atr']].astype('float32')
    
    except Exception as e:
        log(f"Error calculating indicators: {e}", level="ERROR")
        return None
