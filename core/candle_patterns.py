def is_bullish_engulfing(df):
    try:
        if len(df) < 2:
            return False
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        return prev["close"] < prev["open"] and curr["close"] > curr["open"] and curr["close"] > prev["open"]
    except Exception as e:
        from utils.logger import log
        log(f"❌ Error in is_bullish_engulfing: {e}", level='ERROR')
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
        log(f"❌ Error in is_bearish_engulfing: {e}", level='ERROR')
        return False

def is_breakout_candle(df, direction=None):
    try:
        if len(df) < 3:
            return False
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        next_candle = df.iloc[-3] if len(df) >= 3 else None
        price_movement = abs(curr["close"] - prev["close"]) / prev["close"]
        is_breakout = price_movement >= 0.01 and curr["volume"] > 1.5 * prev["volume"]

        # Fake breakout check: confirm with next candle
        if next_candle is not None:
            if direction == "LONG" and next_candle["close"] <= prev["high"]:
                return False
            if direction == "SHORT" and next_candle["close"] >= prev["low"]:
                return False

        if direction:
            if direction == "LONG":
                is_breakout = is_breakout and curr["high"] > prev["high"] and curr["close"] > prev["close"]
            elif direction == "SHORT":
                is_breakout = is_breakout and curr["low"] < prev["low"] and curr["close"] < prev["close"]

        return is_breakout
    except Exception as e:
        from utils.logger import log
        log(f"❌ Error in is_breakout_candle: {e}", level='ERROR')
        return False

def is_doji(df):
    try:
        if len(df) < 1:
            return False
        curr = df.iloc[-1]
        body = abs(curr["open"] - curr["close"])
        range_candle = curr["high"] - curr["low"]
        return body <= 0.1 * range_candle and range_candle > 0
    except Exception as e:
        from utils.logger import log
        log(f"❌ Error in is_doji: {e}", level='ERROR')
        return False

def is_hammer(df):
    try:
        if len(df) < 1:
            return False
        curr = df.iloc[-1]
        body = abs(curr["open"] - curr["close"])
        lower_shadow = curr["open"] - curr["low"] if curr["close"] > curr["open"] else curr["close"] - curr["low"]
        upper_shadow = curr["high"] - curr["close"] if curr["close"] > curr["open"] else curr["high"] - curr["open"]
        return lower_shadow >= 2 * body and upper_shadow <= 0.5 * body and body > 0
    except Exception as e:
        from utils.logger import log
        log(f"❌ Error in is_hammer: {e}", level='ERROR')
        return False

def is_shooting_star(df):
    try:
        if len(df) < 1:
            return False
        curr = df.iloc[-1]
        body = abs(curr["open"] - curr["close"])
        upper_shadow = curr["high"] - curr["close"] if curr["close"] > curr["open"] else curr["high"] - curr["open"]
        lower_shadow = curr["open"] - curr["low"] if curr["close"] > curr["open"] else curr["close"] - curr["low"]
        return upper_shadow >= 2 * body and lower_shadow <= 0.5 * body and body > 0
    except Exception as e:
        from utils.logger import log
        log(f"❌ Error in is_shooting_star: {e}", level='ERROR')
        return False

def is_three_white_soldiers(df):
    try:
        if len(df) < 3:
            return False
        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
        return (c1["close"] > c1["open"] and c2["close"] > c2["open"] and c3["close"] > c3["open"] and
                c1["close"] > c1["open"] * 1.01 and c2["close"] > c2["open"] * 1.01 and c3["close"] > c3["open"] * 1.01 and
                c2["close"] > c1["close"] and c3["close"] > c2["close"])
    except Exception as e:
        from utils.logger import log
        log(f"❌ Error in is_three_white_soldiers: {e}", level='ERROR')
        return False

def is_three_black_crows(df):
    try:
        if len(df) < 3:
            return False
        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
        return (c1["close"] < c1["open"] and c2["close"] < c2["open"] and c3["close"] < c3["open"] and
                c1["open"] > c1["close"] * 1.01 and c2["open"] > c2["close"] * 1.01 and c3["open"] > c3["close"] * 1.01 and
                c2["close"] < c1["close"] and c3["close"] < c2["close"])
    except Exception as e:
        from utils.logger import log
        log(f"❌ Error in is_three_black_crows: {e}", level='ERROR')
        return False
