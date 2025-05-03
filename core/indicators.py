import pandas as pd
import numpy as np
import talib

def safe_talib_call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception:
        return np.nan

async def calculate_indicators(symbol, ohlcv_15m, ohlcv_1h):
    try:
        df_15m = pd.DataFrame(ohlcv_15m, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df_1h = pd.DataFrame(ohlcv_1h, columns=["timestamp", "open", "high", "low", "close", "volume"])

        for df in [df_15m, df_1h]:
            df["ema_20"] = safe_talib_call(talib.EMA, df["close"], timeperiod=20)
            df["rsi"] = safe_talib_call(talib.RSI, df["close"], timeperiod=14)
            df["macd"], df["macdsignal"], _ = safe_talib_call(talib.MACD, df["close"], 12, 26, 9)

        latest_15m = df_15m.iloc[-1]
        latest_1h = df_1h.iloc[-1]

        conditions = {
            "long": (
                latest_15m["close"] > latest_15m["ema_20"] > 0 and
                latest_15m["macd"] > latest_15m["macdsignal"] and
                latest_15m["rsi"] > 55 and
                latest_1h["macd"] > latest_1h["macdsignal"] and
                latest_1h["rsi"] > 50
            ),
            "short": (
                latest_15m["close"] < latest_15m["ema_20"] > 0 and
                latest_15m["macd"] < latest_15m["macdsignal"] and
                latest_15m["rsi"] < 45 and
                latest_1h["macd"] < latest_1h["macdsignal"] and
                latest_1h["rsi"] < 50
            )
        }

        direction = None
        if conditions["long"]:
            direction = "LONG"
        elif conditions["short"]:
            direction = "SHORT"

        confidence = 0
        if direction:
            confidence += 20 if latest_15m["volume"] > df_15m["volume"].mean() else -10
            confidence += 30 if abs(latest_15m["macd"] - latest_15m["macdsignal"]) > 0.5 else 10
            confidence += 20 if direction == "LONG" and latest_1h["rsi"] > 60 else 0
            confidence += 20 if direction == "SHORT" and latest_1h["rsi"] < 40 else 0

        tp_possibility = "HIGH" if confidence >= 70 else "MEDIUM" if confidence >= 50 else "LOW"

        df_15m["direction"] = direction
        df_15m["confidence"] = confidence
        df_15m["tp_possibility"] = tp_possibility

        return df_15m
    except Exception:
        return None
