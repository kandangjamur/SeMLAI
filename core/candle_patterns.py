def is_bullish_engulfing(df):
    """
    Detects a bullish engulfing pattern in the last 2 candles.
    """
    if len(df) < 2:
        return False

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    return (
        prev['close'] < prev['open'] and
        curr['close'] > curr['open'] and
        curr['close'] > prev['open'] and
        curr['open'] < prev['close']
    )

def is_breakout_candle(df):
    """
    Detects breakout candle with large body + high volume
    """
    if len(df) < 2:
        return False

    curr = df.iloc[-1]
    body = abs(curr['close'] - curr['open'])
    range_ = curr['high'] - curr['low']
    body_ratio = body / range_ if range_ > 0 else 0

    volume = curr['volume']
    volume_avg = df['volume'].rolling(window=20).mean().iloc[-1]

    return body_ratio > 0.6 and volume > 1.5 * volume_avg
