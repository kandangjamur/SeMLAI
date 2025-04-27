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
        confidence += 20
    if latest["rsi"] > 55 and latest["volume"] > 1.5 * latest["volume_sma"]:
        confidence += 15
    if latest["macd"] > latest["macd_signal"]:
        confidence += 15
    if pd.notna(latest["adx"]) and latest["adx"] > 20:
        confidence += 10
    if latest["stoch_rsi"] < 0.2:
        confidence += 10
    if is_bullish_engulfing(df): confidence += 10
    if is_breakout_candle(df): confidence += 10

    price = latest["close"]
    atr = latest["atr"]
    sr = detect_sr_levels(df)
    support = sr.get("support")
    resistance = sr.get("resistance")
    midpoint = round((support + resistance) / 2, 3) if support and resistance else None

    fib = calculate_fibonacci_levels(price, direction="LONG")
    tp1 = round(fib.get("tp1", price + atr * 2), 3)
    tp2 = round(fib.get("tp2", price + atr * 3.5), 3)
    tp3 = round(fib.get("tp3", price + atr * 5), 3)
    sl = round(support if support else price - atr * 1.8, 3)

    if confidence < 75:
        return None

    trade_type = (
        "Scalping" if 75 <= confidence < 85 else
        "Normal" if confidence >= 85 else "Spot"
    )

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

def calculate_dynamic_possibilities(confidence, distance_tp1, distance_tp2, distance_tp3):
    # Dynamic calculation based on confidence
    tp1_possibility = min(100, max(50, confidence * (1 - distance_tp1 / 100)))
    tp2_possibility = min(100, max(50, confidence * (1 - distance_tp2 / 100)))
    tp3_possibility = min(100, max(50, confidence * (1 - distance_tp3 / 100)))
    
    return tp1_possibility, tp2_possibility, tp3_possibility

def predict_trend(symbol, ohlcv):
    closes = [c[4] for c in ohlcv]
    # Predict based on the trend
    if closes[-1] > closes[-2] > closes[-3]:
        return "LONG"
    elif closes[-1] < closes[-2] < closes[-3]:
        return "SHORT"
    return "NEUTRAL"  # Remove Neutral in the prediction logic if you want to ensure long/short only

def generate_trade_signal(symbol, ohlcv, exchange):
    indicators = calculate_indicators(symbol, ohlcv)
    if not indicators:
        return None

    confidence = indicators["confidence"]

    if confidence < 50:
        return None  # Discard low-confidence signals

    # Calculate dynamic possibilities
    distance_tp1 = indicators["tp1"] - indicators["price"]
    distance_tp2 = indicators["tp2"] - indicators["price"]
    distance_tp3 = indicators["tp3"] - indicators["price"]
    
    tp1_possibility, tp2_possibility, tp3_possibility = calculate_dynamic_possibilities(
        confidence, distance_tp1, distance_tp2, distance_tp3
    )

    # Prediction now based on the dynamic conditions
    prediction = predict_trend(symbol, ohlcv)
    if prediction == "NEUTRAL":
        return None  # Avoid sending neutral signals

    # Return the dynamic signal format
    signal = {
        "symbol": indicators["symbol"],
        "confidence": confidence,
        "prediction": prediction,  # Direction based on trend
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
