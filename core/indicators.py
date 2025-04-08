import pandas as pd
import numpy as np
import ta

# ✅ Full indicator calculator for combined analysis
def calculate_indicators(df):
    df = df.copy()

    # Drop rows with missing values first
    df.dropna(inplace=True)

    # RSI
    df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()

    # MACD
    macd = ta.trend.MACD(close=df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()

    # EMA 12 & EMA 26
    df['ema_12'] = ta.trend.EMAIndicator(close=df['close'], window=12).ema_indicator()
    df['ema_26'] = ta.trend.EMAIndicator(close=df['close'], window=26).ema_indicator()

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_lower'] = bb.bollinger_lband()

    # Volume Spike (Volume % change)
    df['volume_change'] = df['volume'].pct_change() * 100

    # ATR
    df['atr'] = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14).average_true_range()

    # Drop rows again after indicator calculation
    df.dropna(inplace=True)

    return df

# ✅ Mini individual indicator functions
def get_rsi(df, period=14):
    df = df.copy()
    df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=period).rsi()
    df.dropna(inplace=True)
    return df

def get_macd(df):
    df = df.copy()
    macd = ta.trend.MACD(close=df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df.dropna(inplace=True)
    return df

def get_ema(df, period=21):
    df = df.copy()
    df[f'ema_{period}'] = ta.trend.EMAIndicator(close=df['close'], window=period).ema_indicator()
    df.dropna(inplace=True)
    return df
