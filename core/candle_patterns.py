def is_bullish_engulfing(df):
    c1 = df.iloc[-2]
    c2 = df.iloc[-1]
    return c1["close"] < c1["open"] and c2["close"] > c2["open"] and c2["close"] > c1["open"] and c2["open"] < c1["close"]

def is_breakout_candle(df):
    last_candle = df.iloc[-1]
    prev_high = df["high"][:-1].max()
    return last_candle["close"] > prev_high
