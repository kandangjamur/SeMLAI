def predict_trend(symbol, ohlcv):
    try:
        import pandas as pd
        import ta

        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
        macd = ta.trend.MACD(df["close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()

        last = df.iloc[-1]
        if last["rsi"] > 50 and last["macd"] > last["macd_signal"]:
            return "LONG"
        elif last["rsi"] < 50 and last["macd"] < last["macd_signal"]:
            return "SHORT"
        else:
            return "LONG"  # default fallback
    except Exception as e:
        return "LONG"
