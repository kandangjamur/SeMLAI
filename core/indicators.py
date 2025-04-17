import pandas as pd
import ta

def calculate_indicators(symbol, ohlcv):
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["ema_20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    df["ema_50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    macd = ta.trend.MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range()
    df["volume_sma"] = df["volume"].rolling(window=20).mean()

    if len(df) < 50:
        return None

    latest = df.iloc[-1]
    confidence = 0

    # Hedge-fund level logic
    if latest["ema_20"] > latest["ema_50"]:
        confidence += 30
    if 50 < latest["rsi"] < 75:
        confidence += 20
    if latest["macd"] > latest["macd_signal"]:
        confidence += 20
    if latest["volume"] > 1.8 * latest["volume_sma"]:
        confidence += 15
    if latest["atr"] > 0.5:
        confidence += 10

    # Trade Type
    if confidence >= 75:
        trade_type = "Normal"
    elif confidence >= 60:
        trade_type = "Scalping"
    else:
        return None  # skip low confidence

    close = latest["close"]
    tp1 = round(close * 1.015, 3)
    tp2 = round(close * 1.035, 3)
    tp3 = round(close * 1.065, 3)
    sl = round(close * 0.975, 3)

    leverage = (
        0 if trade_type == "Spot" else
        20 if confidence < 70 else
        35 if confidence < 85 else
        50
    )

    return {
        "symbol": symbol,
        "price": close,
        "confidence": confidence,
        "trade_type": trade_type,
        "timestamp": latest["timestamp"],
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "sl": sl,
        "leverage": leverage
    }
