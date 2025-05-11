import pandas as pd
     import numpy as np

     def is_bullish_engulfing(df):
         try:
             if len(df) < 2:
                 return pd.Series(0.0, index=df.index, dtype="float32")
             close = df['close']
             open_ = df['open']
             conditions = (
                 (close > open_) &
                 (open_.shift(1) > close.shift(1)) &
                 (close > open_.shift(1)) &
                 (open_ < close.shift(1))
             )
             return pd.Series(conditions, index=df.index, dtype="float32").fillna(0.0)
         except Exception as e:
             return pd.Series(0.0, index=df.index, dtype="float32")

     def is_bearish_engulfing(df):
         try:
             if len(df) < 2:
                 return pd.Series(0.0, index=df.index, dtype="float32")
             close = df['close']
             open_ = df['open']
             conditions = (
                 (close < open_) &
                 (open_.shift(1) < close.shift(1)) &
                 (close < open_.shift(1)) &
                 (open_ > close.shift(1))
             )
             return pd.Series(conditions, index=df.index, dtype="float32").fillna(0.0)
         except Exception as e:
             return pd.Series(0.0, index=df.index, dtype="float32")

     def is_doji(df):
         try:
             close = df['close']
             open_ = df['open']
             high = df['high']
             low = df['low']
             body = abs(close - open_)
             range_ = high - low
             conditions = (body <= 0.1 * range_)
             return pd.Series(conditions, index=df.index, dtype="float32").fillna(0.0)
         except Exception as e:
             return pd.Series(0.0, index=df.index, dtype="float32")

     def is_hammer(df):
         try:
             close = df['close']
             open_ = df['open']
             high = df['high']
             low = df['low']
             body = abs(close - open_)
             lower_shadow = open_.where(close > open_, close) - low
             upper_shadow = high - close.where(close > open_, open_)
             range_ = high - low
             conditions = (
                 (lower_shadow > 2 * body) &
                 (upper_shadow < 0.3 * body) &
                 (range_ > 0)
             )
             return pd.Series(conditions, index=df.index, dtype="float32").fillna(0.0)
         except Exception as e:
             return pd.Series(0.0, index=df.index, dtype="float32")

     def is_shooting_star(df):
         try:
             close = df['close']
             open_ = df['open']
             high = df['high']
             low = df['low']
             body = abs(close - open_)
             upper_shadow = high - close.where(close > open_, open_)
             lower_shadow = open_.where(close > open_, close) - low
             range_ = high - low
             conditions = (
                 (upper_shadow > 2 * body) &
                 (lower_shadow < 0.3 * body) &
                 (range_ > 0)
             )
             return pd.Series(conditions, index=df.index, dtype="float32").fillna(0.0)
         except Exception as e:
             return pd.Series(0.0, index=df.index, dtype="float32")

     def is_three_white_soldiers(df):
         try:
             if len(df) < 3:
                 return pd.Series(0.0, index=df.index, dtype="float32")
             close = df['close']
             open_ = df['open']
             conditions = (
                 (close > open_) &
                 (close.shift(1) > open_.shift(1)) &
                 (close.shift(2) > open_.shift(2)) &
                 (close > close.shift(1)) &
                 (close.shift(1) > close.shift(2))
             )
             return pd.Series(conditions, index=df.index, dtype="float32").fillna(0.0)
         except Exception as e:
             return pd.Series(0.0, index=df.index, dtype="float32")

     def is_three_black_crows(df):
         try:
             if len(df) < 3:
                 return pd.Series(0.0, index=df.index, dtype="float32")
             close = df['close']
             open_ = df['open']
             conditions = (
                 (close < open_) &
                 (close.shift(1) < open_.shift(1)) &
                 (close.shift(2) < open_.shift(2)) &
                 (close < close.shift(1)) &
                 (close.shift(1) < close.shift(2))
             )
             return pd.Series(conditions, index=df.index, dtype="float32").fillna(0.0)
         except Exception as e:
             return pd.Series(0.0, index=df.index, dtype="float32")
