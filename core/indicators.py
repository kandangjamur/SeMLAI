import pandas as pd
import ta

def calculate_indicators(symbol, ohlcv):
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])

    # Indicators
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

    # --- Dynamic Confidence Logic ---

    # EMA Crossover
    ema_gap = latest["ema_20"] - latest["ema_50"]
    if ema_gap > 0:
        confidence += min(ema_gap / latest["close"] * 100, 25)  # up to +25

    # RSI strength
    if latest["rsi"] > 50:
        confidence += min((latest["rsi"] - 50) * 0.5, 20)  # up to +20

    # MACD crossover
    macd_diff = latest["macd"] - latest["macd_signal"]
    if macd_diff > 0:
        confidence += min(macd_diff * 50, 20)  # up to +20

    # Volume spike
    vol_spike = latest["volume"] / latest["volume_sma"] if latest["volume_sma"] > 0 else 1
    if vol_spike > 1:
        confidence += min((vol_spike - 1) * 10, 15)  # up to +15

    # ATR volatility
    if latest["atr"] > 0:
        confidence += min(latest["atr"] / latest["close"] * 100, 10)  # up to +10

    # Final trade type
    if confidence >= 75:
        trade_type = "Normal"
    elif confidence >= 60:
        trade_type = "Scalping"
    else:
        return None  # discard low-quality trades

    # Set dynamic leverage
    if trade_type == "Scalping":
        leverage = min(int(vol_spike * 20), 50)
    elif trade_type == "Normal":
        leverage = min(int(vol_spike * 10), 25)
    else:
        leverage = 1

    # Direction placeholder (will be set in predict_trend)
    prediction = "LONG"

    # Set dynamic TP and SL
    close = latest["close"]
    atr = latest["atr"]

    if prediction == "LONG":
        tp1 = round(close + atr * 1.2, 3)
        tp2 = round(close + atr * 2, 3)
        tp3 = round(close + atr * 3.5, 3)
        sl = round(close - atr * 1.2, 3)
    else:  # SHORT
        tp1 = round(close - atr * 1.2, 3)
        tp2 = round(close - atr * 2, 3)
        tp3 = round(close - atr * 3.5, 3)
        sl = round(close + atr * 1.2, 3)

    return {
        "symbol": symbol,
        "price": close,
        "confidence": round(confidence, 2),
        "trade_type": trade_type,
        "timestamp": latest["timestamp"],
        "atr": atr,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "sl": sl,
        "leverage": leverage
    }
