import pandas as pd
import ta

def calculate_indicators(symbol, ohlcv):
    if len(ohlcv) < 50:
        return None

    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["ema_20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    df["ema_50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    macd = ta.trend.MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range()
    df["volume_sma"] = df["volume"].rolling(window=20).mean()

    latest = df.iloc[-1]
    confidence = 0

    # EMA crossover
    if latest["ema_20"] > latest["ema_50"]:
        confidence += 25

    # RSI strength
    if latest["rsi"] > 55:
        confidence += 20

    # MACD bullish
    if latest["macd"] > latest["macd_signal"]:
        confidence += 20

    # Volume spike
    if latest["volume"] > 1.5 * latest["volume_sma"]:
        confidence += 15

    # Volatility check
    if latest["atr"] > 0:
        confidence += 10

    # Trade Type
    if confidence >= 75:
        trade_type = "Normal"
    elif confidence >= 60:
        trade_type = "Scalping"
    else:
        return None  # discard very low confidence

    price = latest["close"]

    # Dynamically adjusted TP & SL
    if trade_type == "Scalping":
        tp1 = round(price * 1.005, 4)   # 0.5%
        tp2 = round(price * 1.01, 4)    # 1%
        tp3 = round(price * 1.015, 4)   # 1.5%
        sl = round(price * 0.99, 4)     # -1%
    else:  # Normal
        tp1 = round(price * 1.015, 4)   # 1.5%
        tp2 = round(price * 1.03, 4)    # 3%
        tp3 = round(price * 1.05, 4)    # 5%
        sl = round(price * 0.975, 4)    # -2.5%

    # Dynamic Leverage: Scalp gets higher, Normal more stable
    if trade_type == "Scalping":
        leverage = min(50, max(20, confidence))
    else:
        leverage = min(20, max(5, confidence // 5))

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
        "leverage": leverage
    }
