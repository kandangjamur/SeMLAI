import pandas as pd
import ta

def calculate_indicators(symbol, ohlcv):
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    
    if len(df) < 50:
        return None

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

    # === Hedge-fund level Indicator Checks ===
    if latest["ema_20"] > latest["ema_50"]:
        confidence += 25  # EMA crossover
    if latest["rsi"] > 50:
        confidence += 20  # RSI bullish
    if latest["macd"] > latest["macd_signal"]:
        confidence += 20  # MACD crossover
    if latest["volume"] > 1.5 * latest["volume_sma"]:
        confidence += 15  # Volume spike
    if latest["atr"] > 0:
        confidence += 10  # Volatility present

    # === Determine Trade Type ===
    if confidence >= 75:
        trade_type = "Normal"
    elif confidence >= 60:
        trade_type = "Scalping"
    else:
        return None  # Ignore weak setups

    # === TP / SL ===
    price = latest["close"]
    atr = latest["atr"]
    tp1 = round(price + (atr * 1.2), 3)
    tp2 = round(price + (atr * 2.2), 3)
    tp3 = round(price + (atr * 3.2), 3)
    sl = round(price - (atr * 1.1), 3)

    # === Direction will be added later in analysis ===
    # === Dynamic Leverage ===
    volatility_factor = atr / price if price > 0 else 0
    volume_factor = latest["volume"] / latest["volume_sma"] if latest["volume_sma"] > 0 else 0

    base_leverage = 5
    if trade_type == "Scalping":
        base_leverage += (confidence - 75) * 0.8
    elif trade_type == "Normal":
        base_leverage += (confidence - 85) * 1.2

    # Add boost from volatility and volume
    base_leverage += volatility_factor * 30
    base_leverage += volume_factor * 2

    leverage = min(round(base_leverage), 50)

    return {
        "symbol": symbol,
        "price": price,
        "confidence": round(confidence, 2),
        "trade_type": trade_type,
        "timestamp": latest["timestamp"],
        "atr": atr,
        "tp1": round(tp1, 3),
        "tp2": round(tp2, 3),
        "tp3": round(tp3, 3),
        "sl": round(sl, 3),
        "leverage": f"{leverage}x"
    }
