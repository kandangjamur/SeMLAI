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
        confidence += 20

    # RSI in bullish zone (only add 15 points if RSI > 60, to be more selective)
    if latest["rsi"] > 60:
        confidence += 15

    # MACD Bullish (we'll only add 15 if MACD > Signal by a certain margin)
    if latest["macd"] > latest["macd_signal"] and (latest["macd"] - latest["macd_signal"]) > 0.01:
        confidence += 15

    # Volume spike (increase the multiplier for more strictness)
    if latest["volume"] > 2 * latest["volume_sma"]:
        confidence += 10

    # ATR confirms volatility (adjust for stricter volatility condition)
    if latest["atr"] > 0.5:
        confidence += 10

    # Skip weak signals below 65%
    if confidence < 65:
        return None

    # Trade Type Logic (as per your rules)
    if confidence >= 90:
        trade_type = "Spot"
    elif 75 <= confidence < 90:
        trade_type = "Normal"
    else:  # 65 <= confidence < 75
        trade_type = "Scalping"

    close = latest["close"]

    # TP / SL Calculation
    tp1 = round(close * 1.01, 3)
    tp2 = round(close * 1.03, 3)
    tp3 = round(close * 1.05, 3)
    sl = round(close * 0.98, 3)

    # ✅ Dynamic Leverage (unchanged)
    if trade_type == "Spot":
        leverage = 1
    elif trade_type == "Scalping":
        leverage = round(min(50, max(10, latest["atr"] * 100)), 1)
    else:  # Normal
        leverage = round(min(20, max(5, latest["atr"] * 50)), 1)

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
