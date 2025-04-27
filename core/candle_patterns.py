def is_bullish_engulfing(df):
    if len(df) < 2:
        return False
    last_candle = df.iloc[-1]
    prev_candle = df.iloc[-2]
    return last_candle["close"] > last_candle["open"] and prev_candle["close"] < prev_candle["open"]

def is_breakout_candle(df):
    if len(df) < 2:
        return False
    last_candle = df.iloc[-1]
    prev_candle = df.iloc[-2]
    return last_candle["high"] > prev_candle["high"] and last_candle["low"] > prev_candle["low"]
