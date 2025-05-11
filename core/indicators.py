import pandas as pd
import numpy as np
from utils.logger import log

def calculate_indicators(df):
    try:
        df = df.copy()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=14).mean()
        
        # Volume
        df['volume'] = df['volume'].astype('float32')
        
        # Bollinger Bands
        window = 20
        df['sma_20'] = df['close'].rolling(window=window).mean()
        df['std_20'] = df['close'].rolling(window=window).std()
        df['bb_upper'] = df['sma_20'] + (2 * df['std_20'])
        df['bb_lower'] = df['sma_20'] - (2 * df['std_20'])
        
        # Volume SMA 20
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        
        # Fill NaN values
        df = df.fillna(0.0)
        
        log("Indicators calculated: RSI, MACD, ATR, Volume, Bollinger Bands, Volume SMA 20")
        return df
    except Exception as e:
        log(f"Error calculating indicators: {e}", level="ERROR")
        return None
