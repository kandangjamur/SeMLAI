import pandas as pd
import ta
from utils.support_resistance import detect_sr_levels
from utils.fibonacci import calculate_fibonacci_levels
from core.candle_patterns import is_bullish_engulfing, is_breakout_candle

def calculate_indicators(symbol, ohlcv):
    try:
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        if df["close"].isnull().mean() > 0.1:
            return None

        df["ema_20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
        df["ema_50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
        macd = ta.trend.MACD(df["close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range()
        df["stoch_rsi"] = ta.momentum.StochRSIIndicator(df["close"]).stochrsi_k()
        df["adx"] = ta.trend.ADXIndicator(df["high"], df["low"], df["close"]).adx()

        latest = df.iloc[-1]

        confidence = 0
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
        fib = calculate_fibonacci_levels(price, direction="LONG")
        tp1 = round(fib.get("tp1", price + atr * 1.5), 3)
        tp2 = round(fib.get("tp2", price + atr * 2.5), 3)
        tp3 = round(fib.get("tp3", price + atr * 4), 3)

        sr = detect_sr_levels(df)
        support = sr.get("support")
        resistance = sr.get("resistance")

        sl = round(support if support else price - atr * 2, 3)

        trade_type = "Normal" if confidence >= 85 else "Scalping"

        leverage = 20  # Placeholder, will override from real leverage check

        possibility = min(confidence + 5, 99)

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
            "possibility": possibility
        }

    except Exception as e:
        print(f"❌ Indicator calc error {symbol}: {e}")
        return None
