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
        df = df.dropna()
        df = df[(df['close'] > 0) & (df['high'] > 0) & (df['low'] > 0) & (df['volume'] > 0)]
        df = df[df['high'] > df['low']]

        if len(df) < 50:
            log(f"⚠️ Insufficient valid data for {symbol}: {len(df)} rows")
            return None

        if df['close'].std() <= 0 or df['volume'].mean() < 1000:
            log(f"⚠️ Low volatility or volume for {symbol}: std={df['close'].std()}, avg_volume={df['volume'].mean()}")
            return None

        df["ema_20"] = ta.trend.EMAIndicator(df["close"], window=20, fillna=True).ema_indicator()
        df["ema_50"] = ta.trend.EMAIndicator(df["close"], window=50, fillna=True).ema_indicator()
        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14, fillna=True).rsi()
        macd = ta.trend.MACD(df["close"], fillna=True)
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], fillna=True).average_true_range()
        df["vwap"] = calculate_vwap(df)

        try:
            if (df['high'] - df['low']).eq(0).any() or df['close'].eq(0).any():
                log(f"⚠️ Invalid data for ADX calculation for {symbol}")
                df["adx"] = np.nan
            else:
                adx = ta.trend.ADXIndicator(df["high"], df["low"], df["close"], window=14, fillna=True).adx()
                if adx.isna().all() or adx.eq(0).all():
                    log(f"⚠️ ADX returned invalid values for {symbol}")
                    df["adx"] = np.nan
                else:
                    df["adx"] = adx
        except Exception as e:
            log(f"⚠️ ADX calculation failed for {symbol}: {e}")
            df["adx"] = np.nan

        df["stoch_rsi"] = ta.momentum.StochRSIIndicator(df["close"], fillna=True).stochrsi_k()

        latest = df.iloc[-1]
        direction = "LONG" if latest["ema_20"] > latest["ema_50"] else "SHORT"
        confidence = 0

        # LONG conditions
        if direction == "LONG":
            confidence += 20 if latest["ema_20"] > latest["ema_50"] else 0
            confidence += 15 if latest["rsi"] > 55 else 0
            confidence += 15 if latest["macd"] > latest["macd_signal"] else 0
            confidence += 10 if not np.isnan(latest["adx"]) and latest["adx"] > 20 else 0
            confidence += 10 if latest["stoch_rsi"] < 0.3 else 0
            confidence += 10 if is_bullish_engulfing(df) else 0
            confidence += 10 if is_breakout_candle(df) else 0
            confidence += 10 if latest["close"] > latest["vwap"] else 0
            confidence += 15 if calculate_rsi_divergence(df["close"], df["rsi"]) else 0
        # SHORT conditions
        else:
            confidence += 20 if latest["ema_20"] < latest["ema_50"] else 0
            confidence += 15 if latest["rsi"] < 45 else 0
            confidence += 15 if latest["macd"] < latest["macd_signal"] else 0
            confidence += 10 if not np.isnan(latest["adx"]) and latest["adx"] > 20 else 0
            confidence += 10 if latest["stoch_rsi"] > 0.7 else 0
            confidence += 10 if is_bearish_engulfing(df) else 0
            confidence += 10 if is_breakout_candle(df, direction="SHORT") else 0
            confidence += 10 if latest["close"] < latest["vwap"] else 0
            confidence += 15 if calculate_rsi_divergence(df["close"], df["rsi"]) else 0

        # Volatility Filter
        if latest["atr"] < df["atr"][-10:].mean() * 0.5:
            log(f"⚠️ Low volatility for {symbol}: atr={latest['atr']}")
            return None

        price = latest["close"]
        atr = latest["atr"]
        fib = calculate_fibonacci_levels(price, direction=direction)
        tp1 = round(fib.get("tp1", price + atr * 1.2 if direction == "LONG" else price - atr * 1.2), 4)
        tp2 = round(fib.get("tp2", price + atr * 2.0 if direction == "LONG" else price - atr * 2.0), 4)
        tp3 = round(fib.get("tp3", price + atr * 3.0 if direction == "LONG" else price - atr * 3.0), 4)

        sr = detect_sr_levels(df)
        support = sr.get("support")
        resistance = sr.get("resistance")

        sl = round(support if support and direction == "LONG" else resistance if resistance and direction == "SHORT" else price - atr * 0.8 if direction == "LONG" else price + atr * 0.8, 4)
        trade_type = "Normal" if confidence >= 85 else "Scalping"
        leverage = 20
        possibility = min(confidence + 5, 99)

        signal = {
            "symbol": symbol,
            "price": price,
            "direction": direction,
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

        log(f"✅ Indicators calculated for {symbol}: direction={direction}, confidence={confidence}")
        return signal

    except Exception as e:
        log(f"❌ Error calculating indicators for {symbol}: {e}")
        return None

def calculate_vwap(df):
    try:
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        return (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()
    except:
        return df["close"]

def calculate_rsi_divergence(prices, rsi):
    try:
        if len(prices) < 3 or len(rsi) < 3:
            return False
        price_diff = prices.iloc[-1] - prices.iloc[-2]
        rsi_diff = rsi.iloc[-1] - rsi.iloc[-2]
        return (price_diff > 0 and rsi_diff < 0) or (price_diff < 0 and rsi_diff > 0)
    except:
        return False

def is_bearish_engulfing(df):
    try:
        if len(df) < 2:
            return False
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        return (prev["close"] > prev["open"] and 
                curr["open"] > curr["close"] and 
                curr["open"] >= prev["close"] and 
                curr["close"] <= prev["open"])
    except:
        return False
