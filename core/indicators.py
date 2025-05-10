import pandas as pd
import numpy as np
from numba import jit
from utils.logger import log

@jit(nopython=True)
def calculate_rsi(data, periods=14):
    delta = np.diff(data)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    
    avg_gain = np.zeros_like(data)
    avg_loss = np.zeros_like(data)
    
    avg_gain[periods] = np.mean(gain[:periods])
    avg_loss[periods] = np.mean(loss[:periods])
    
    for i in range(periods + 1, len(data)):
        avg_gain[i] = (avg_gain[i-1] * (periods - 1) + gain[i-1]) / periods
        avg_loss[i] = (avg_loss[i-1] * (periods - 1) + loss[i-1]) / periods
    
    rs = np.where(avg_loss != 0, avg_gain / avg_loss, 0)
    rsi = 100 - (100 / (1 + rs))
    return rsi

@jit(nopython=True)
def calculate_macd(prices, fast=12, slow=26, signal=9):
    def ema(data, period):
        alpha = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        return ema
    
    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    macd = ema_fast - ema_slow
    
    signal_line = ema(macd, signal)
    return macd, signal_line

def calculate_indicators(df: pd.DataFrame):
    try:
        if len(df) < 26:  # Minimum for MACD
            log("Insufficient data for indicators", level="WARNING")
            return None
            
        df = df.copy()
        
        # RSI
        df['rsi'] = np.nan
        df['rsi'].iloc[14:] = calculate_rsi(df['close'].values, periods=14)[14:]
        
        # MACD
        macd, signal = calculate_macd(df['close'].values)
        df['macd'] = macd
        df['macd_signal'] = signal
        
        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(window=14).mean()
        
        # Fill NaN with reasonable defaults
        df['rsi'] = df['rsi'].fillna(50.0)
        df['macd'] = df['macd'].fillna(0.0)
        df['macd_signal'] = df['macd_signal'].fillna(0.0)
        df['atr'] = df['atr'].fillna(df['atr'].mean())
        
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'rsi', 'macd', 'macd_signal', 'atr']]
    
    except Exception as e:
        log(f"Error calculating indicators: {e}", level="ERROR")
        return None
