import pandas as pd
import ta

def calculate_indicators(df):
    """Calculates various indicators used for technical analysis."""
    # Calculating EMA, RSI, MACD, ATR, etc.
    df["ema_20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    df["ema_50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    df["macd"] = ta.trend.MACD(df["close"]).macd()
    df["macd_signal"] = ta.trend.MACD(df["close"]).macd_signal()
    df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range()
    df["stoch_rsi"] = ta.momentum.StochRSIIndicator(df["close"]).stochrsi_k()
    df["adx"] = ta.trend.ADXIndicator(df["high"], df["low"], df["close"]).adx()
    df["volume_sma"] = df["volume"].rolling(window=20).mean()

    return df

def get_indicator_values(df):
    """Extracts the latest indicator values."""
    latest = df.iloc[-1].to_dict()

    indicators = {
        "ema_20": latest["ema_20"],
        "ema_50": latest["ema_50"],
        "rsi": latest["rsi"],
        "macd": latest["macd"],
        "macd_signal": latest["macd_signal"],
        "atr": latest["atr"],
        "stoch_rsi": latest["stoch_rsi"],
        "adx": latest["adx"],
        "volume_sma": latest["volume_sma"]
    }

    return indicators
