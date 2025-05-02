def is_bullish_engulfing(df):
    try:
        if len(df) < 2:
            return False
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        return prev["close"] < prev["open"] and curr["close"] > curr["open"] and curr["close"] > prev["open"]
    except Exception as e:
        from utils.logger import log
        log(f"❌ Error in is_bullish_engulfing: {e}")
        return False

def is_bearish_engulfing(df):
    try:
        if len(df) < 2:
            return False
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        return prev["close"] > prev["open"] and curr["open"] > curr["close"] and curr["open"] >= prev["close"] and curr["close"] <= prev["open"]
    except Exception as e:
        from utils.logger import log
        log(f"❌ Error in is_bearish_engulfing: {e}")
        return False

def is_breakout_candle(df, direction=None):
    try:
        if len(df) < 2:
            return False
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        price_movement = abs(curr["close"] - prev["close"]) / prev["close"]
        is_breakout = price_movement >= 0.01 and curr["volume"] > prev["volume"]

        if direction:
            if direction == "LONG":
                is_breakout = is_breakout and curr["high"] > prev["high"] and curr["close"] > prev["close"]
            elif direction == "SHORT":
                is_breakout = is_breakout and curr["low"] < prev["low"] and curr["close"] < prev["close"]

        return is_breakout
    except Exception as e:
        from utils.logger import log
        log(f"❌ Error in is_breakout_candle: {e}")
        return False
