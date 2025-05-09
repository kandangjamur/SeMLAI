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
        macd = ta.trend.MACD(df["close"], window_slow=26, window_fast=12, window_sign=9, fillna=True)
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2, fillna=True)
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_lower"] = bb.bollinger_lband()
        
        # ATR
        df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=14, fillna=True).average_true_range()

        # Moving Averages
        df["sma_50"] = ta.trend.SMAIndicator(df["close"], window=50, fillna=True).sma_indicator()
        df["sma_200"] = ta.trend.SMAIndicator(df["close"], window=200, fillna=True).sma_indicator()

        # Handle NaN values explicitly
        df.fillna({
            "rsi": 50.0,
            "macd": 0.0,
            "macd_signal": 0.0,
            "bb_upper": df["close"] * 1.02,
            "bb_lower": df["close"] * 0.98,
            "atr": df["atr"].mean() if not df["atr"].isna().all() else 0.0,
            "sma_50": df["close"].mean() if not df["close"].isna().all() else 0.0,
            "sma_200": df["close"].mean() if not df["close"].isna().all() else 0.0
        }, inplace=True)

        if df.isna().any().any():
            log("NaN values detected after filling in indicators", level='WARNING')
            return None

        return df
    except Exception as e:
        log(f"Error in calculate_indicators: {str(e)}", level="ERROR")
        return None
