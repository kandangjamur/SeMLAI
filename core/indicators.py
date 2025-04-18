import pandas as pd
import ta

def calculate_indicators(symbol, ohlcv):
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])

    # Basic indicators
    df["ema_20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    df["ema_50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    macd = ta.trend.MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range()
    df["volume_sma"] = df["volume"].rolling(window=20).mean()

    # Check data sufficiency
    if len(df) < 50 or df.iloc[-1].isnull().any():
        return None

    latest = df.iloc[-1]
    confidence = 0

    # Indicator scoring
    if latest["ema_20"] > latest["ema_50"]:
        confidence += 25

    if latest["rsi"] > 55:
        confidence += 20
    elif latest["rsi"] < 45:
        confidence -= 10  # bearish RSI

    if latest["macd"] > latest["macd_signal"]:
        confidence += 20

    if latest["volume"] > 1.5 * latest["volume_sma"]:
        confidence += 15

    if latest["atr"] > 0:
        confidence += 10

    # Trade classification
    if confidence >= 75:
        trade_type = "Normal"
    elif confidence >= 60:
        trade_type = "Scalping"
    else:
        return None  # discard weak signals

    close = latest["close"]
    atr = latest["atr"]

    # Dynamic TP/SL using ATR
    tp1 = round(close + 1.5 * atr, 3)
    tp2 = round(close + 3 * atr, 3)
    tp3 = round(close + 5 * atr, 3)
    sl = round(close - 1.8 * atr, 3)

    # Short logic (optional, if trend prediction is Short)
    # You'll flip these in analysis.py if direction is SHORT

    signal = {
        "symbol": symbol,
        "price": close,
        "confidence": round(confidence, 2),
        "trade_type": trade_type,
        "timestamp": latest["timestamp"],
        "atr": atr,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "sl": sl
    }

    # Debug print for dev logs
    print(f"[DEBUG] {symbol} | Confidence: {confidence}% | Type: {trade_type}")

    return signal
