import pandas as pd
import ta
from utils.support_resistance import detect_sr_levels
from utils.fibonacci import calculate_fibonacci_levels
from core.candle_patterns import is_bullish_engulfing, is_breakout_candle
import numpy as np
from utils.logger import log

def calculate_indicators(symbol, ohlcv):
    try:
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        # ڈیٹا کی صفائی
        df = df.dropna()
        df = df[(df['close'] != 0) & (df['high'] != 0) & (df['low'] != 0) & (df['volume'] != 0)]
        
        if len(df) < 50:
            log(f"⚠️ Insufficient valid data for {symbol}: {len(df)} rows")
            return None

        # انڈیکیٹرز کیلکولیٹ کریں
        df["ema_20"] = ta.trend.EMAIndicator(df["close"], window=20, fillna=True).ema_indicator()
        df["ema_50"] = ta.trend.EMAIndicator(df["close"], window=50, fillna=True).ema_indicator()
        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14, fillna=True).rsi()
        macd = ta.trend.MACD(df["close"], fillna=True)
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], fillna=True).average_true_range()
        df["adx"] = ta.trend.ADXIndicator(df["high"], df["low"], df["close"], window=14, fillna=True).adx()
        df["stoch_rsi"] = ta.momentum.StochRSIIndicator(df["close"], fillna=True).stochrsi_k()

        latest = df.iloc[-1]
        confidence = 0
        confidence += 20 if latest["ema_20"] > latest["ema_50"] else 0
        confidence += 15 if latest["rsi"] > 55 else 0
        confidence += 15 if latest["macd"] > latest["macd_signal"] else 0
        confidence += 10 if latest["adx"] > 20 else 0
        confidence += 10 if latest["stoch_rsi"] < 0.2 else 0
        confidence += 10 if is_bullish_engulfing(df) else 0
        confidence += 10 if is_breakout_candle(df) else 0

        price = latest["close"]
        atr = latest["atr"]
        fib = calculate_fibonacci_levels(price, direction="LONG")
        tp1 = round(fib.get("tp1", price + atr * 1.5), 4)
        tp2 = round(fib.get("tp2", price + atr * 2.5), 4)
        tp3 = round(fib.get("tp3", price + atr * 4), 4)

        sr = detect_sr_levels(df)
        support = sr.get("support")
        resistance = sr.get("resistance")

        sl = round(support if support else price - atr * 2, 4)
        trade_type = "Normal" if confidence >= 85 else "Scalping"
        leverage = 20
        possibility = min(confidence + 5, 99)

        signal = {
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

        log(f"✅ Indicators calculated for {symbol}: confidence={confidence}")
        return signal

    except Exception as e:
        log(f"❌ Error calculating indicators for {symbol}: {e}")
        return None
