import pandas as pd
import ta

def calculate_indicators(symbol, ohlcv_15m, ohlcv_1h, ohlcv_4h):
    def build_df(ohlcv):
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["ema_20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
        df["ema_50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
        macd = ta.trend.MACD(df["close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range()
        df["volume_sma"] = df["volume"].rolling(window=20).mean()
        return df

    df_15m = build_df(ohlcv_15m)
    df_1h = build_df(ohlcv_1h)
    df_4h = build_df(ohlcv_4h)

    if len(df_15m) < 50 or len(df_1h) < 50 or len(df_4h) < 50:
        return None

    latest_15m = df_15m.iloc[-1]
    latest_1h = df_1h.iloc[-1]
    latest_4h = df_4h.iloc[-1]

    confidence = 0

    # ✅ Multi-timeframe trend agreement
    if latest_15m["ema_20"] > latest_15m["ema_50"] and latest_1h["ema_20"] > latest_1h["ema_50"] and latest_4h["ema_20"] > latest_4h["ema_50"]:
        confidence += 30

    # ✅ RSI boost
    if latest_15m["rsi"] > 50:
        confidence += 10
    if latest_1h["rsi"] > 50:
        confidence += 10

    # ✅ MACD agreement
    if latest_15m["macd"] > latest_15m["macd_signal"]:
        confidence += 10
    if latest_1h["macd"] > latest_1h["macd_signal"]:
        confidence += 10

    # ✅ Volume spike
    if latest_15m["volume"] > latest_15m["volume_sma"] * 1.5:
        confidence += 10

    # ✅ Candle pattern boost (hammer/engulfing detection)
    candle_range = latest_15m["high"] - latest_15m["low"]
    body = abs(latest_15m["close"] - latest_15m["open"])
    upper_wick = latest_15m["high"] - max(latest_15m["close"], latest_15m["open"])
    lower_wick = min(latest_15m["close"], latest_15m["open"]) - latest_15m["low"]

    # Hammer or pin bar
    if lower_wick > candle_range * 0.4 and body < candle_range * 0.4:
        confidence += 5

    # Rejection (doji)
    if body < candle_range * 0.1:
        return None  # skip doji candles

    close_price = latest_15m["close"]
    atr = latest_15m["atr"]

    # Trade type
    trade_type = "Scalping" if confidence < 75 else "Normal"

    return {
        "symbol": symbol,
        "price": close_price,
        "confidence": confidence,
        "trade_type": trade_type,
        "timestamp": latest_15m["timestamp"],
        "atr": atr
    }
