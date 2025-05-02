# core/indicators.py
import pandas as pd
import numpy as np
import ta
from utils.logger import log
from utils.support_resistance import detect_sr_levels
from utils.fibonacci import calculate_fibonacci_levels
from core.candle_patterns import is_bullish_engulfing, is_breakout_candle, is_bearish_engulfing

def calculate_indicators(symbol, ohlcv):
    try:
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]).dropna()
        if len(df) < 50 or df["close"].std() <= 0 or df["volume"].mean() < 1000:
            return None

        df["ema_20"] = ta.trend.EMAIndicator(df["close"], 20).ema_indicator()
        df["ema_50"] = ta.trend.EMAIndicator(df["close"], 50).ema_indicator()
        df["rsi"] = ta.momentum.RSIIndicator(df["close"], 14).rsi()
        macd = ta.trend.MACD(df["close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range()
        df["stoch_rsi"] = ta.momentum.StochRSIIndicator(df["close"]).stochrsi_k()

        latest = df.iloc[-1]
        direction = "LONG" if latest["ema_20"] > latest["ema_50"] else "SHORT"
        confidence = 0

        if direction == "LONG":
            confidence += 20 if latest["rsi"] > 60 else 0
            confidence += 20 if latest["macd"] > latest["macd_signal"] else 0
            confidence += 10 if latest["stoch_rsi"] < 0.25 else 0
            confidence += 10 if is_bullish_engulfing(df) else 0
        else:
            confidence += 20 if latest["rsi"] < 40 else 0
            confidence += 20 if latest["macd"] < latest["macd_signal"] else 0
            confidence += 10 if latest["stoch_rsi"] > 0.75 else 0
            confidence += 10 if is_bearish_engulfing(df) else 0

        price = latest["close"]
        atr = latest["atr"]
        fib = calculate_fibonacci_levels(price, direction=direction)
        tp1 = fib.get("tp1", price + atr * 1.5 if direction == "LONG" else price - atr * 1.5)
        tp2 = fib.get("tp2", price + atr * 2.0 if direction == "LONG" else price - atr * 2.0)
        tp3 = fib.get("tp3", price + atr * 3.0 if direction == "LONG" else price - atr * 3.0)
        sr = detect_sr_levels(df)
        sl = sr["support"] if direction == "LONG" else sr["resistance"]

        return {
            "symbol": symbol,
            "price": price,
            "direction": direction,
            "confidence": confidence,
            "tp1": round(tp1, 4),
            "tp2": round(tp2, 4),
            "tp3": round(tp3, 4),
            "sl": round(sl, 4) if sl else round(price - atr * 0.8 if direction == "LONG" else price + atr * 0.8, 4),
            "atr": atr,
            "timestamp": latest["timestamp"],
            "trade_type": "Normal" if confidence >= 85 else "Scalping"
        }
    except Exception as e:
        log(f"Error calculating indicators for {symbol}: {e}")
        return None
