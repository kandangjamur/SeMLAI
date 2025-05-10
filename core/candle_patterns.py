import pandas as pd
import numpy as np

def is_bullish_engulfing(df):
    if len(df) < 2:
        return pd.Series(False, index=df.index)
    prev_candle = df.iloc[-2]
    curr_candle = df.iloc[-1]
    return (prev_candle['close'] < prev_candle['open'] and
            curr_candle['close'] > curr_candle['open'] and
            curr_candle['open'] <= prev_candle['close'] and
            curr_candle['close'] >= prev_candle['open'])

def is_bearish_engulfing(df):
    if len(df) < 2:
        return pd.Series(False, index=df.index)
    prev_candle = df.iloc[-2]
    curr_candle = df.iloc[-1]
    return (prev_candle['close'] > prev_candle['open'] and
            curr_candle['close'] < curr_candle['open'] and
            curr_candle['open'] >= prev_candle['close'] and
            curr_candle['close'] <= prev_candle['open'])

def is_doji(df):
    if len(df) < 1:
        return pd.Series(False, index=df.index)
    candle = df.iloc[-1]
    body = abs(candle['close'] - candle['open'])
    range_candle = candle['high'] - candle['low']
    return body <= 0.1 * range_candle if range_candle > 0 else False

def is_hammer(df):
    if len(df) < 1:
        return pd.Series(False, index=df.index)
    candle = df.iloc[-1]
    body = abs(candle['close'] - candle['open'])
    lower_shadow = candle['open'] - candle['low'] if candle['close'] > candle['open'] else candle['close'] - candle['low']
    upper_shadow = candle['high'] - candle['close'] if candle['close'] > candle['open'] else candle['high'] - candle['open']
    return (lower_shadow >= 2 * body and upper_shadow <= 0.3 * body and body > 0)

def is_shooting_star(df):
    if len(df) < 1:
        return pd.Series(False, index=df.index)
    candle = df.iloc[-1]
    body = abs(candle['close'] - candle['open'])
    upper_shadow = candle['high'] - candle['close'] if candle['close'] > candle['open'] else candle['high'] - candle['open']
    lower_shadow = candle['open'] - candle['low'] if candle['close'] > candle['open'] else candle['close'] - candle['low']
    return (upper_shadow >= 2 * body and lower_shadow <= 0.3 * body and body > 0)

def is_three_white_soldiers(df):
    if len(df) < 3:
        return pd.Series(False, index=df.index)
    last_three = df.iloc[-3:]
    return all(
        last_three['close'] > last_three['open'] &
        (last_three['close'] > last_three['open'].shift(1)) &
        (last_three['close'].shift(1) > last_three['open'].shift(2))
    )

def is_three_black_crows(df):
    if len(df) < 3:
        return pd.Series(False, index=df.index)
    last_three = df.iloc[-3:]
    return all(
        last_three['close'] < last_three['open'] &
        (last_three['close'] < last_three['open'].shift(1)) &
        (last_three['close'].shift(1) < last_three['open'].shift(2))
    )
