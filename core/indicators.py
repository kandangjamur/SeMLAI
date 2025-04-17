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
        confidence += 30
    if latest["rsi"] > 55:
        confidence += 20
    if latest["macd"] > latest["macd_signal"]:
        confidence += 20
    if latest["volume"] > 1.5 * latest["volume_sma"]:
        confidence += 15
    if latest["atr"] > 0:
        confidence += 10

    # Trade Type Logic
    if confidence >= 75:
        trade_type = "Normal"
    else:
        trade_type = "Scalping"

    price = latest["close"]
    tp1 = round(price * 1.02, 4)
    tp2 = round(price * 1.04, 4)
    tp3 = round(price * 1.06, 4)
    sl = round(price * 0.97, 4)

    # Leverage based on confidence
    if trade_type == "Scalping":
        leverage = 20 + int((confidence - 60) * 2)
    else:
        leverage = 10 + int((confidence - 75) * 2.5)

    return {
        "symbol": symbol,
        "price": price,
        "confidence": confidence,
        "trade_type": trade_type,
        "timestamp": latest["timestamp"],
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "sl": sl,
        "leverage": min(leverage, 50)
    }
