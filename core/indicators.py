import pandas as pd
import numpy as np
import ta
from utils.logger import log

def calculate_indicators(df):
    try:
        if len(df) < 50 or df['close'].std() <= 0:
            log("Insufficient data for indicators", level='WARNING')
            return None

        df = df.copy()
        df = df.astype({'close': 'float32', 'high': 'float32', 'low': 'float32', 'volume': 'float32'})

        # RSI
        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14, fillna=True).rsi()
        
        # MACD
        df["macd"] = ta.trend.MACD(df["close"], window_slow=26, window_fast=12, window_sign=9, fillna=True).macd()
        df["macd_signal"] = ta.trend.MACD(df["close"], window_slow=26, window_fast=12, window_sign=9, fillna=True).macd_signal()
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2, fillna=True)
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_lower"] = bb.bollinger_lband()
        
        # ATR
        df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=14, fillna=True).average_true_range()
        
        # Ichimoku Cloud
        df["ichimoku_a"] = ta.trend.IchimokuIndicator(df["high"], df["low"], window1=9, window2=26, window3=52, fillna=True).ichimoku_a()
        df["ichimoku_b"] = ta.trend.IchimokuIndicator(df["high"], df["low"], window1=9, window2=26, window3=52, fillna=True).ichimoku_b()
        
        # OBV
        df["obv"] = ta.volume.OnBalanceVolumeIndicator(df["close"], df["volume"], fillna=True).on_balance_volume()
        
        # Simple Moving Average (instead of HMA)
        df["sma"] = ta.trend.SMAIndicator(df["close"], window=9, fillna=True).sma_indicator()
        
        # Stochastic RSI
        df["stoch_rsi"] = ta.momentum.StochasticRSIIndicator(df["close"], window=14, smooth1=3, smooth2=3, fillna=True).stochrsi_k()

        if df.isna().any().any() or df.isin([np.inf, -np.inf]).any().any():
            log("NaN or Inf values in indicators", level='WARNING')
            return None

        log(f"Indicators calculated for {len(df)} rows")
        return df
    except Exception as e:
        log(f"Error calculating indicators: {e}", level='ERROR')
        return None
