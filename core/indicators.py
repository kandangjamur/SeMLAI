import ta
import pandas as pd

def calculate_indicators(ohlcv):
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    if df.empty or len(df) < 50:
        return None

    try:
        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
        df["ema_fast"] = ta.trend.EMAIndicator(df["close"], window=9).ema_indicator()
        df["ema_slow"] = ta.trend.EMAIndicator(df["close"], window=21).ema_indicator()

        latest = df.iloc[-1]
        if pd.isna(latest["rsi"]) or pd.isna(latest["ema_fast"]) or pd.isna(latest["ema_slow"]):
            return None

        if latest["ema_fast"] > latest["ema_slow"] and latest["rsi"] > 60:
            return {"direction": "LONG", "confidence": 75}
        elif latest["ema_fast"] < latest["ema_slow"] and latest["rsi"] < 40:
            return {"direction": "SHORT", "confidence": 73}
        else:
            return {"direction": None, "confidence": 45}
    except Exception:
        return None
