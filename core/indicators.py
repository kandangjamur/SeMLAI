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

    if latest["ema_20"] > latest["ema_50"]:
        confidence += 25
    if latest["rsi"] > 55:
        confidence += 15
    if latest["macd"] > latest["macd_signal"]:
        confidence += 20
    if latest["volume"] > 1.5 * latest["volume_sma"]:
        confidence += 15
    if latest["atr"] > 0:
        confidence += 10

    # Decide trade type based on confidence
    if confidence < 60:
        return None  # Below threshold
    elif confidence < 75:
        trade_type = "Scalping"
    else:
        trade_type = "Normal"

    return {
        "symbol": symbol,
        "price": latest["close"],
        "confidence": confidence,
        "trade_type": trade_type,
        "timestamp": latest["timestamp"],
        "atr": latest["atr"]
    }
