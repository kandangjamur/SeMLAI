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

    if latest["ema_20"] > latest["ema_50"]: confidence += 20
    if latest["rsi"] > 55: confidence += 15
    if latest["macd"] > latest["macd_signal"]: confidence += 15
    if latest["volume"] > 1.5 * latest["volume_sma"]: confidence += 15
    if latest["atr"] > 0: confidence += 10

    price = latest["close"]
    atr = latest["atr"]

    tp1 = round(price + atr * 1.5, 3)
    tp2 = round(price + atr * 3, 3)
    tp3 = round(price + atr * 5, 3)
    sl = round(price - atr * 1.5, 3)

    if confidence >= 90:
        trade_type = "Normal"
    elif confidence >= 80:
        trade_type = "Scalping"
    else:
        return None  # filter weak signals

    leverage = min(max(int(confidence / 2), 3), 50)

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
        "atr": atr,
        "leverage": leverage
    }
