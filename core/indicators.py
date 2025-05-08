import pandas as pd
import numpy as np
import ta
from utils.logger import log

def calculate_indicators(df):
    try:
        if len(df) < 30 or df['close'].std() <= 0:
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

        # Moving Averages
        df["sma_50"] = ta.trend.SMAIndicator(df["close"], window=50, fillna=True).sma_indicator()
        df["sma_200"] = ta.trend.SMAIndicator(df["close"], window=200, fillna=True).sma_indicator()

        return df
    except Exception as e:
        log(f"Error in calculate_indicators: {str(e)}", level="ERROR")
        return None
