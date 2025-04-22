import pandas as pd
import ta
from utils.fibonacci import calculate_fibonacci_levels
from utils.support_resistance import detect_sr_levels
from core.candle_patterns import is_bullish_engulfing, is_breakout_candle

def calculate_indicators(symbol, ohlcv):
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])

    # Get Support/Resistance levels
    sr = detect_sr_levels(df)
    support = sr["support"]
    resistance = sr["resistance"]
    midpoint = round((support + resistance) / 2, 3) if support and resistance else None

    # Calculate technical indicators
    df["ema_20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    df["ema_50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range()
    macd = ta.trend.MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["stoch_rsi"] = ta.momentum.StochRSIIndicator(df["close"]).stochrsi_k()
    df["adx"] = ta.trend.ADXIndicator(df["high"], df["low"], df["close"]).adx()
    df["volume_sma"] = df["volume"].rolling(window=20).mean()

    if len(df) < 50:
        return None

    latest = df.iloc[-1].to_dict()  # ✅ Fix applied here

    confidence = 0
    if latest["ema_20"] > latest["ema_50"]:
        confidence += 20
    if latest["rsi"] > 55 and latest["volume"] > 1.5 * latest["volume_sma"]:
        confidence += 15
    if latest["macd"] > latest["macd_signal"]:
        confidence += 15
    if latest["adx"] > 20:
        confidence += 10
    if latest["stoch_rsi"] < 0.2:
        confidence += 10
    if is_bullish_engulfing(df):
        confidence += 10
    if is_breakout_candle(df):
        confidence += 10

    price = latest["close"]
    atr = latest["atr"]

    # Fibonacci-based TP levels
    fib_levels = calculate_fibonacci_levels(price, direction="LONG")
    fib_tp1, fib_tp2, fib_tp3 = fib_levels.get("tp1"), fib_levels.get("tp2"), fib_levels.get("tp3")

    tp1 = round(fib_tp1 if fib_tp1 else price + atr * 2, 3)
    tp2 = round(fib_tp2 if fib_tp2 else price + atr * 3.5, 3)
    tp3 = round(fib_tp3 if fib_tp3 else price + atr * 5, 3)
    sl = round(support if support else price - atr * 1.8, 3)

    if confidence < 80:
        return None

    trade_type = "Scalping" if 80 <= confidence < 90 else "Normal"
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
        "leverage": leverage,
        "support": support,
        "resistance": resistance,
        "midpoint": midpoint
    }
