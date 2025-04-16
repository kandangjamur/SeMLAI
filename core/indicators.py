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

    # EMA Crossover
    if latest["ema_20"] > latest["ema_50"]:
        confidence += 25

    # RSI in bullish zone
    if latest["rsi"] > 50:
        confidence += 20

    # MACD Bullish
    if latest["macd"] > latest["macd_signal"]:
        confidence += 20

    # Volume spike
    if latest["volume"] > 1.5 * latest["volume_sma"]:
        confidence += 15

    # ATR confirms volatility
    if latest["atr"] > 0:
        confidence += 10

    # Trade Type
    if confidence >= 90:
        trade_type = "Spot"
    elif confidence >= 75:
        trade_type = "Normal"
    else:
        trade_type = "Scalping"

    close = latest["close"]

    # TP / SL
    tp1 = round(close * 1.01, 3)
    tp2 = round(close * 1.03, 3)
    tp3 = round(close * 1.05, 3)
    sl = round(close * 0.98, 3)

    # Leverage (example logic - you can update)
    leverage = 3 if trade_type == "Scalping" else (2 if trade_type == "Normal" else 1)

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
