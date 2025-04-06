import ta
import pandas as pd

def calculate_indicators(df):
    df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
    macd = ta.trend.MACD(df['close'])
    df['macd_diff'] = macd.macd_diff()
    df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
    return df

def is_ema_crossover(df):
    return df['ema_12'].iloc[-2] < df['ema_26'].iloc[-2] and df['ema_12'].iloc[-1] > df['ema_26'].iloc[-1]

def is_rsi_oversold(df):
    return df['rsi'].iloc[-1] < 30

def is_macd_bullish(df):
    return df['macd_diff'].iloc[-1] > 0
