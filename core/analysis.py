import pandas as pd
import ta
from utils.support_resistance import detect_sr_levels
from utils.fibonacci import calculate_fibonacci_levels
from core.candle_patterns import is_bullish_engulfing, is_breakout_candle

def calculate_indicators(symbol, ohlcv):
    if not ohlcv or len(ohlcv) < 50:
        return None

    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])

    # Adding technical indicators
    df["ema_20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    df["ema_50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    df["macd"] = ta.trend.MACD(df["close"]).macd()
    df["macd_signal"] = ta.trend.MACD(df["close"]).macd_signal()
    df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range()
    df["stoch_rsi"] = ta.momentum.StochRSIIndicator(df["close"]).stochrsi_k()
    df["adx"] = ta.trend.ADXIndicator(df["high"], df["low"], df["close"]).adx()
    df["volume_sma"] = df["volume"].rolling(window=20).mean()

    latest = df.iloc[-1].to_dict()
    confidence = 0

    # Indicator-based scoring system
    if latest["ema_20"] > latest["ema_50"]:
        confidence += 20
    if latest["rsi"] > 55:
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
    sr = detect_sr_levels(df)
    support = sr.get("support")
    resistance = sr.get("resistance")

    # Fibonacci levels for target prices
    fib = calculate_fibonacci_levels(price, direction="LONG")
    tp1 = round(fib.get("tp1", price + atr * 1.5), 3)
    tp2 = round(fib.get("tp2", price + atr * 2.5), 3)
    tp3 = round(fib.get("tp3", price + atr * 4), 3)
    sl = round(support if support else price - atr * 2, 3)

    # Setting trade type based on confidence score
    if confidence >= 85:
        trade_type = "Normal"
    elif 75 <= confidence < 85:
        trade_type = "Scalping"
    else:
        return None

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
        "resistance": resistance
    }
