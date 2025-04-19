import pandas as pd
import ta

def calculate_indicators(symbol, ohlcv_15m, ohlcv_1h):
    df_15m = pd.DataFrame(ohlcv_15m, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df_1h = pd.DataFrame(ohlcv_1h, columns=["timestamp", "open", "high", "low", "close", "volume"])

    for df in [df_15m, df_1h]:
        df["ema_20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
        df["ema_50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
        macd = ta.trend.MACD(df["close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range()
        df["volume_sma"] = df["volume"].rolling(window=20).mean()

    if len(df_15m) < 50 or len(df_1h) < 50:
        return None

    l_15m = df_15m.iloc[-1]
    l_1h = df_1h.iloc[-1]

    confidence = 0

    # === Weighted confidence scoring ===
    if l_15m["ema_20"] > l_15m["ema_50"] and l_1h["ema_20"] > l_1h["ema_50"]:
        confidence += 25

    if l_15m["rsi"] > 50 and l_1h["rsi"] > 55:
        confidence += 20

    if l_15m["macd"] > l_15m["macd_signal"] and l_1h["macd"] > l_1h["macd_signal"]:
        confidence += 20

    if l_15m["volume"] > 1.5 * l_15m["volume_sma"]:
        confidence += 15

    if l_15m["atr"] > 0 and l_1h["atr"] > 0:
        confidence += 10

    trade_type = "Normal" if confidence >= 75 else "Scalping"
    price = l_15m["close"]
    atr = l_15m["atr"]

    # Dynamic leverage logic
    leverage = 20 if trade_type == "Scalping" else 35
    if atr > 1.5:
        leverage = min(50, leverage + 5)

    return {
        "symbol": symbol,
        "price": price,
        "confidence": confidence,
        "trade_type": trade_type,
        "timestamp": l_15m["timestamp"],
        "atr": atr,
        "leverage": leverage
    }
