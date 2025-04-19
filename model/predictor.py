def predict_trend(symbol, ohlcv):
    import pandas as pd
    import ta

    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["ema_20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    df["ema_50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    macd = ta.trend.MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()

    latest = df.iloc[-1]

    if (
        latest["ema_20"] > latest["ema_50"]
        and latest["rsi"] > 50
        and latest["macd"] > latest["macd_signal"]
    ):
        return "LONG"
    else:
        return "SHORT"
