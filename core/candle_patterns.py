def is_bullish_engulfing(df):
    if len(df) < 2:
        return False
    prev = df.iloc[-2]
    curr = df.iloc[-1]
    return prev['close'] < prev['open'] and curr['close'] > curr['open'] and curr['close'] > prev['open'] and curr['open'] < prev['close']

def is_breakout_candle(df):
    if len(df) < 10:
        return False
    recent_high = df['high'].iloc[-10:-1].max()
    last_close = df['close'].iloc[-1]
    return last_close > recent_high
