# core/indicators.py
import pandas as pd
import ta
from utils.fibonacci import calculate_fibonacci_levels
from utils.support_resistance import detect_sr_levels
from core.candle_patterns import is_bullish_engulfing, is_breakout_candle

def calculate_indicators(symbol, ohlcv):
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["ema_20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    df["ema_50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(df["close"]).rsi()
    df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range()
    macd = ta.trend.MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["stoch_rsi"] = ta.momentum.StochRSIIndicator(df["close"]).stochrsi_k()
    df["adx"] = ta.trend.ADXIndicator(df["high"], df["low"], df["close"]).adx()
    df["volume_sma"] = df["volume"].rolling(20).mean()

    latest = df.iloc[-1]
    confidence = 0
    if latest["ema_20"] > latest["ema_50"]: confidence += 20
    if latest["rsi"] > 55 and latest["volume"] > 1.5 * latest["volume_sma"]: confidence += 15
    if latest["macd"] > latest["macd_signal"]: confidence += 15
    if latest["adx"] > 20: confidence += 10
    if latest["stoch_rsi"] < 0.2: confidence += 10
    if is_bullish_engulfing(df): confidence += 10
    if is_breakout_candle(df): confidence += 10

    price = latest["close"]
    atr = latest["atr"]
    sr = detect_sr_levels(df)
    support = sr.get("support")
    resistance = sr.get("resistance")

    fib = calculate_fibonacci_levels(price, "LONG")
    tp1, tp2, tp3 = fib["tp1"], fib["tp2"], fib["tp3"]
    sl = support or round(price - atr * 2, 3)

    if confidence < 75:
        return None

    trade_type = "Normal" if confidence >= 85 else "Scalping"
    leverage = min(max(int(confidence / 2), 3), 50)

    return {
        "symbol": symbol,
        "price": price,
        "confidence": confidence,
        "trade_type": trade_type,
        "timestamp": latest["timestamp"],
        "tp1": round(tp1, 3),
        "tp2": round(tp2, 3),
        "tp3": round(tp3, 3),
        "tp1_chance": 95 if confidence > 90 else 85,
        "tp2_chance": 87 if confidence > 90 else 75,
        "tp3_chance": 70 if confidence > 90 else 60,
        "sl": round(sl, 3),
        "atr": atr,
        "leverage": leverage,
        "support": support,
        "resistance": resistance
    }
