import pandas as pd
import ta

def calculate_indicators(symbol, ohlcv_15m, ohlcv_1h):
    df_15m = pd.DataFrame(ohlcv_15m, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df_1h = pd.DataFrame(ohlcv_1h, columns=["timestamp", "open", "high", "low", "close", "volume"])

    if len(df_15m) < 50 or len(df_1h) < 50:
        return None

    # Add indicators to both
    for df in [df_15m, df_1h]:
        df["ema20"] = ta.trend.EMAIndicator(df["close"], 20).ema_indicator()
        df["ema50"] = ta.trend.EMAIndicator(df["close"], 50).ema_indicator()
        df["rsi"] = ta.momentum.RSIIndicator(df["close"]).rsi()
        macd = ta.trend.MACD(df["close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range()
        df["volume_sma"] = df["volume"].rolling(window=20).mean()

    l15 = df_15m.iloc[-1]
    l1h = df_1h.iloc[-1]

    confidence = 0
    weights = {}

    # === Weighted scoring ===
    if l15["ema20"] > l15["ema50"] and l1h["ema20"] > l1h["ema50"]:
        confidence += 25
        weights['ema_crossover'] = True
    if l15["rsi"] > 50 and l1h["rsi"] > 55:
        confidence += 20
        weights['rsi_strength'] = True
    if l15["macd"] > l15["macd_signal"] and l1h["macd"] > l1h["macd_signal"]:
        confidence += 25
        weights['macd'] = True
    if l15["volume"] > 1.5 * l15["volume_sma"]:
        confidence += 10
        weights['volume_spike'] = True
    if l15["atr"] > 0 and l1h["atr"] > 0:
        confidence += 10
        weights['atr_ok'] = True

    # Trade type classification
    if confidence >= 75:
        trade_type = "Normal"
    else:
        trade_type = "Scalping"

    # Volatility-based leverage
    atr = l15["atr"]
    if trade_type == "Scalping":
        leverage = 25 if atr < 0.5 else 35
    else:
        leverage = 35 if atr < 0.8 else 50

    # TP/SL based on ATR + prediction direction
    price = l15["close"]
    tp1 = round(price + atr * 1.2, 3)
    tp2 = round(price + atr * 2.0, 3)
    tp3 = round(price + atr * 3.0, 3)
    sl = round(price - atr * 1.0, 3)

    return {
        "symbol": symbol,
        "price": price,
        "confidence": confidence,
        "trade_type": trade_type,
        "atr": atr,
        "leverage": leverage,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "sl": sl,
        "timestamp": l15["timestamp"],
        "debug": weights  # helpful for seeing what contributed
    }
