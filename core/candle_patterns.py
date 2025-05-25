import pandas as pd
import numpy as np


def is_doji(df, doji_ratio=0.1):
    """
    Identify doji candles (open and close are very close)

    Args:
        df: DataFrame with OHLCV data
        doji_ratio: Maximum ratio of body to range for doji classification

    Returns:
        Series of boolean values where True indicates a doji
    """
    df = df.copy()

    # Calculate body and range
    df['body'] = abs(df['close'] - df['open'])
    df['range'] = df['high'] - df['low']

    # To avoid division by zero
    df['range'] = df['range'].replace(0, np.nan)

    # Calculate body/range ratio
    df['body_range_ratio'] = df['body'] / df['range']

    # Identify doji (body is small compared to range)
    return df['body_range_ratio'] < doji_ratio


def is_hammer(df, body_ratio=0.3, shadow_ratio=2.0):
    """
    Identify hammer candlesticks (small body, long lower shadow)

    Args:
        df: DataFrame with OHLCV data
        body_ratio: Maximum ratio of body to range
        shadow_ratio: Minimum ratio of lower shadow to body

    Returns:
        Series of boolean values where True indicates a hammer
    """
    df = df.copy()

    # Calculate body and shadows
    df['body'] = abs(df['close'] - df['open'])
    df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
    df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']

    # To avoid division by zero
    df['body'] = df['body'].replace(0, 0.000001)

    # Calculate ratios
    df['body_range_ratio'] = df['body'] / (df['high'] - df['low'])
    df['lower_body_ratio'] = df['lower_shadow'] / df['body']

    # Identify hammers (small body at top, long lower shadow)
    return (df['body_range_ratio'] < body_ratio) & \
           (df['lower_body_ratio'] > shadow_ratio) & \
           (df['upper_shadow'] < df['body'])


def is_shooting_star(df, body_ratio=0.3, shadow_ratio=2.0):
    """
    Identify shooting star candlesticks (small body, long upper shadow)

    Args:
        df: DataFrame with OHLCV data
        body_ratio: Maximum ratio of body to range
        shadow_ratio: Minimum ratio of upper shadow to body

    Returns:
        Series of boolean values where True indicates a shooting star
    """
    df = df.copy()

    # Calculate body and shadows
    df['body'] = abs(df['close'] - df['open'])
    df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
    df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']

    # To avoid division by zero
    df['body'] = df['body'].replace(0, 0.000001)

    # Calculate ratios
    df['body_range_ratio'] = df['body'] / (df['high'] - df['low'])
    df['upper_body_ratio'] = df['upper_shadow'] / df['body']

    # Identify shooting stars (small body at bottom, long upper shadow)
    return (df['body_range_ratio'] < body_ratio) & \
           (df['upper_body_ratio'] > shadow_ratio) & \
           (df['lower_shadow'] < df['body'])


def is_bullish_engulfing(df):
    """
    Identify bullish engulfing pattern (current bullish candle engulfs previous bearish)

    Args:
        df: DataFrame with OHLCV data

    Returns:
        Series of boolean values where True indicates a bullish engulfing
    """
    df = df.copy()

    # Previous candle is bearish (close < open)
    prev_bearish = df['close'].shift(1) < df['open'].shift(1)

    # Current candle is bullish (close > open)
    curr_bullish = df['close'] > df['open']

    # Current candle body engulfs previous candle body
    body_engulfing = (df['open'] <= df['close'].shift(1)) & \
                     (df['close'] >= df['open'].shift(1))

    # Combine conditions
    return prev_bearish & curr_bullish & body_engulfing


def is_bearish_engulfing(df):
    """
    Identify bearish engulfing pattern (current bearish candle engulfs previous bullish)

    Args:
        df: DataFrame with OHLCV data

    Returns:
        Series of boolean values where True indicates a bearish engulfing
    """
    df = df.copy()

    # Previous candle is bullish (close > open)
    prev_bullish = df['close'].shift(1) > df['open'].shift(1)

    # Current candle is bearish (close < open)
    curr_bearish = df['close'] < df['open']

    # Current candle body engulfs previous candle body
    body_engulfing = (df['close'] <= df['open'].shift(1)) & \
                     (df['open'] >= df['close'].shift(1))

    # Combine conditions
    return prev_bullish & curr_bearish & body_engulfing


def is_three_white_soldiers(df, min_body_ratio=0.5, max_upper_shadow_ratio=0.3):
    """
    Identify three white soldiers pattern (three consecutive bullish candles with higher closes)

    Args:
        df: DataFrame with OHLCV data
        min_body_ratio: Minimum ratio of body to range
        max_upper_shadow_ratio: Maximum ratio of upper shadow to body

    Returns:
        Series of boolean values where True indicates three white soldiers
    """
    df = df.copy()

    # Calculate bodies and shadows
    df['body'] = abs(df['close'] - df['open'])
    df['range'] = df['high'] - df['low']
    df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)

    # To avoid division by zero
    df['body'] = df['body'].replace(0, 0.000001)
    df['range'] = df['range'].replace(0, 0.000001)

    # Calculate ratios
    df['body_range_ratio'] = df['body'] / df['range']
    df['upper_shadow_body_ratio'] = df['upper_shadow'] / df['body']

    # Three consecutive bullish candles
    bullish_1 = df['close'].shift(2) > df['open'].shift(2)
    bullish_2 = df['close'].shift(1) > df['open'].shift(1)
    bullish_3 = df['close'] > df['open']

    # Each close higher than previous close
    higher_closes = (df['close'].shift(1) > df['close'].shift(2)) & \
                    (df['close'] > df['close'].shift(1))

    # Each open higher than previous open
    higher_opens = (df['open'].shift(1) > df['open'].shift(2)) & \
                   (df['open'] > df['open'].shift(1))

    # Substantial bodies with small upper shadows
    good_bodies_1 = df['body_range_ratio'].shift(2) > min_body_ratio
    good_bodies_2 = df['body_range_ratio'].shift(1) > min_body_ratio
    good_bodies_3 = df['body_range_ratio'] > min_body_ratio

    small_shadows_1 = df['upper_shadow_body_ratio'].shift(
        2) < max_upper_shadow_ratio
    small_shadows_2 = df['upper_shadow_body_ratio'].shift(
        1) < max_upper_shadow_ratio
    small_shadows_3 = df['upper_shadow_body_ratio'] < max_upper_shadow_ratio

    # Combine conditions
    return bullish_1 & bullish_2 & bullish_3 & \
        higher_closes & higher_opens & \
        good_bodies_1 & good_bodies_2 & good_bodies_3 & \
        small_shadows_1 & small_shadows_2 & small_shadows_3


def is_three_black_crows(df, min_body_ratio=0.5, max_lower_shadow_ratio=0.3):
    """
    Identify three black crows pattern (three consecutive bearish candles with lower closes)

    Args:
        df: DataFrame with OHLCV data
        min_body_ratio: Minimum ratio of body to range
        max_lower_shadow_ratio: Maximum ratio of lower shadow to body

    Returns:
        Series of boolean values where True indicates three black crows
    """
    df = df.copy()

    # Calculate bodies and shadows
    df['body'] = abs(df['close'] - df['open'])
    df['range'] = df['high'] - df['low']
    df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']

    # To avoid division by zero
    df['body'] = df['body'].replace(0, 0.000001)
    df['range'] = df['range'].replace(0, 0.000001)

    # Calculate ratios
    df['body_range_ratio'] = df['body'] / df['range']
    df['lower_shadow_body_ratio'] = df['lower_shadow'] / df['body']

    # Three consecutive bearish candles
    bearish_1 = df['close'].shift(2) < df['open'].shift(2)
    bearish_2 = df['close'].shift(1) < df['open'].shift(1)
    bearish_3 = df['close'] < df['open']

    # Each close lower than previous close
    lower_closes = (df['close'].shift(1) < df['close'].shift(2)) & \
                   (df['close'] < df['close'].shift(1))

    # Each open lower than previous open
    lower_opens = (df['open'].shift(1) < df['open'].shift(2)) & \
                  (df['open'] < df['open'].shift(1))

    # Substantial bodies with small lower shadows
    good_bodies_1 = df['body_range_ratio'].shift(2) > min_body_ratio
    good_bodies_2 = df['body_range_ratio'].shift(1) > min_body_ratio
    good_bodies_3 = df['body_range_ratio'] > min_body_ratio

    small_shadows_1 = df['lower_shadow_body_ratio'].shift(
        2) < max_lower_shadow_ratio
    small_shadows_2 = df['lower_shadow_body_ratio'].shift(
        1) < max_lower_shadow_ratio
    small_shadows_3 = df['lower_shadow_body_ratio'] < max_lower_shadow_ratio

    # Combine conditions
    return bearish_1 & bearish_2 & bearish_3 & \
        lower_closes & lower_opens & \
        good_bodies_1 & good_bodies_2 & good_bodies_3 & \
        small_shadows_1 & small_shadows_2 & small_shadows_3
