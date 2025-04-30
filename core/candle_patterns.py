def is_bullish_engulfing(df):
    if len(df) < 2:
        return False
    prev = df.iloc[-2]
    curr = df.iloc[-1]
    return prev["close"] < prev["open"] and curr["close"] > curr["open"] and curr["close"] > prev["open"]

def is_breakout_candle(df):
    if len(df) < 2:
        return False
    prev = df.iloc[-2]
    curr = df.iloc[-1]
    return curr["high"] > prev["high"] and curr["close"] > prev["close"]
