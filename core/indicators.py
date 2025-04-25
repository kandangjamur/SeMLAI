import pandas as pd
import ta
from utils.fibonacci import calculate_fibonacci_levels
from utils.support_resistance import detect_sr_levels
from core.candle_patterns import is_bullish_engulfing, is_breakout_candle

def calculate_indicators(symbol, ohlcv):
    if len(ohlcv) < 50: return None

    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])

    df["ema_20"] = ta.trend.EMAIndicator(df["close"], 20).ema_indicator()
    df["ema_50"] = ta.trend.EMAIndicator(df["close"], 50).ema_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], 14).rsi()
    df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range()
    macd = ta.trend.MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["stoch_rsi"] = ta.momentum.StochRSIIndicator(df["close"]).stochrsi_k()
    df["adx"] = ta.trend.ADXIndicator(df["high"], df["low"], df["close"]).adx()
    df["volume_sma"] = df["volume"].rolling(window=20).mean()

    latest = df.iloc[-1].to_dict()
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

    fib = calculate_fibonacci_levels(price, direction="LONG")
    tp1 = round(fib.get("tp1", price + atr * 1.2), 3)
    tp2 = round(fib.get("tp2", price + atr * 2.5), 3)
    tp3 = round(fib.get("tp3", price + atr * 4.5), 3)
    sl = round(support if support else price - atr * 1.8, 3)

    if confidence < 75:
        return None

    trade_type = "Scalping" if 75 <= confidence < 85 else "Normal"
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
