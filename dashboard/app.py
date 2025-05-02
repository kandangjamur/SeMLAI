import pandas as pd
import ta
import warnings
from utils.fibonacci import calculate_fibonacci_levels
from utils.support_resistance import detect_sr_levels
from core.candle_patterns import is_bullish_engulfing, is_breakout_candle

warnings.filterwarnings("ignore", category=RuntimeWarning)

def calculate_indicators(symbol, ohlcv):
    if not ohlcv or len(ohlcv) < 50:
        return None

    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])

    if df.isnull().values.any():
        return None

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

    latest = df.iloc[-1].to_dict()
    confidence = 0

    if latest["ema_20"] > latest["ema_50"]:
        confidence += 25
    if latest["rsi"] > 60 and latest["volume"] > 1.5 * latest["volume_sma"]:
        confidence += 20
    if latest["macd"] > latest["macd_signal"]:
        confidence += 20
    if pd.notna(latest["adx"]) and latest["adx"] > 25:
        confidence += 15
    if latest["stoch_rsi"] < 0.25:
        confidence += 10
    if is_bullish_engulfing(df):
        confidence += 15
    if is_breakout_candle(df, direction="LONG"):
        confidence += 15

    price = latest["close"]
    atr = latest["atr"]
    sr = detect_sr_levels(df)
    support = sr.get("support")
    resistance = sr.get("resistance")
    midpoint = round((support + resistance) / 2, 3) if support and resistance else None

    fib = calculate_fibonacci_levels(price, direction="LONG")
    tp1 = round(fib.get("tp1", price + atr * 1.2), 3)
    tp2 = round(fib.get("tp2", price + atr * 2.0), 3)
    tp3 = round(fib.get("tp3", price + atr * 3.0), 3)
    sl = round(support if support else price - atr * 0.8, 3)

    if confidence < 85:
        return None

    trade_type = "Normal" if confidence >= 85 else "Scalping"
    leverage = 10

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

def calculate_dynamic_possibilities(confidence, distance_tp1, distance_tp2, distance_tp3, atr, price):
    volatility_factor = atr / price
    tp1_possibility = round(min(95, confidence + 5 if volatility_factor < 0.02 else confidence), 1)
    tp2_possibility = round(min(85, confidence - 5 if volatility_factor < 0.02 else confidence - 10), 1)
    tp3_possibility = round(min(75, confidence - 15 if volatility_factor < 0.02 else confidence - 20), 1)
    return tp1_possibility, tp2_possibility, tp3_possibility

def predict_trend(symbol, ohlcv):
    closes = [c[4] for c in ohlcv]
    if closes[-1] > closes[-2] > closes[-3]:
        return "LONG"
    elif closes[-1] < closes[-2] < closes[-3]:
        return "SHORT"
    return None

def generate_trade_signal(symbol, ohlcv, exchange):
    indicators = calculate_indicators(symbol, ohlcv)
    if not indicators:
        return None

    confidence = indicators["confidence"]
    if confidence < 85:
        return None

    price = indicators["price"]
    atr = indicators["atr"]
    distance_tp1 = abs(indicators["tp1"] - price)
    distance_tp2 = abs(indicators["tp2"] - price)
    distance_tp3 = abs(indicators["tp3"] - price)

    tp1_possibility, tp2_possibility, tp3_possibility = calculate_dynamic_possibilities(
        confidence, distance_tp1, distance_tp2, distance_tp3, atr, price
    )

    prediction = predict_trend(symbol, ohlcv)
    if not prediction:
        return None

    signal = {
        "symbol": indicators["symbol"],
        "confidence": confidence,
        "prediction": prediction,
        "trade_type": indicators["trade_type"],
        "price": indicators["price"],
        "tp1": indicators["tp1"],
        "tp2": indicators["tp2"],
        "tp3": indicators["tp3"],
        "sl": indicators["sl"],
        "leverage": indicators["leverage"],
        "tp1_possibility": tp1_possibility,
        "tp2_possibility": tp2_possibility,
        "tp3_possibility": tp3_possibility
    }
    return signal
