import pandas as pd
import ta
from utils.support_resistance import detect_sr_levels
from utils.fibonacci import calculate_fibonacci_levels
from core.candle_patterns import is_bullish_engulfing, is_bearish_engulfing, is_breakout_candle, is_doji, is_hammer, is_shooting_star, is_three_white_soldiers, is_three_black_crows
import numpy as np
from utils.logger import log

def calculate_indicators(symbol, ohlcv):
    try:
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]).dropna()
        df = df[(df['close'] > 0) & (df['high'] > 0) & (df['low'] > 0) & (df['volume'] > 0) & (df['high'] > df['low'])]
        
        if len(df) < 50 or df['close'].std() <= 0 or df['volume'].mean() < 100000:
            log(f"[{symbol}] Insufficient data or low volume", level='WARNING')
            return None

        # Existing indicators
        df["ema_20"] = ta.trend.EMAIndicator(df["close"], window=20, fillna=True).ema_indicator()
        df["ema_50"] = ta.trend.EMAIndicator(df["close"], window=50, fillna=True).ema_indicator()
        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14, fillna=True).rsi()
        macd = ta.trend.MACD(df["close"], fillna=True)
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], fillna=True).average_true_range()
        df["vwap"] = calculate_vwap(df)
        df["adx"] = ta.trend.ADXIndicator(df["high"], df["low"], df["close"], window=14, fillna=True).adx()
        df["stoch_rsi"] = ta.momentum.StochRSIIndicator(df["close"], fillna=True).stochrsi_k()
        bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2)
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_lower"] = bb.bollinger_lband()
        df["mfi"] = ta.volume.MFIIndicator(df["high"], df["low"], df["close"], df["volume"]).money_flow_index()
        df["cci"] = ta.trend.CCIIndicator(df["high"], df["low"], df["close"], window=20).cci()
        
        # New indicators
        ichimoku = ta.trend.IchimokuIndicator(df["high"], df["low"], window1=9, window2=26, window3=52, fillna=True)
        df["ichimoku_a"] = ichimoku.ichimoku_a()
        df["ichimoku_b"] = ichimoku.ichimoku_b()
        df["ichimoku_base"] = ichimoku.ichimoku_base_line()
        df["ichimoku_conversion"] = ichimoku.ichimoku_conversion_line()
        df["rvi"] = ta.momentum.RVIIndicator(df["close"], df["open"], fillna=True).rvi()
        df["rvi_signal"] = ta.momentum.RVIIndicator(df["close"], df["open"], fillna=True).rvi_signal()
        df["obv"] = ta.volume.OnBalanceVolumeIndicator(df["close"], df["volume"], fillna=True).on_balance_volume()
        df["volume_sma_20"] = df["volume"].rolling(window=20).mean()
        df["atr_sma_10"] = df["atr"].rolling(window=10).mean()
        df["hma_9"] = calculate_hma(df["close"], 9)

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Volume and volatility filter
        if latest["volume"] < 1.5 * latest["volume_sma_20"] or latest["atr"] < 0.75 * latest["atr_sma_10"]:
            log(f"[{symbol}] Low volume or volatility", level='WARNING')
            return None

        direction = "LONG" if latest["ema_20"] > latest["ema_50"] else "SHORT"
        confidence = 0
        indicators_used = []

        # LONG signal confidence
        if direction == "LONG":
            if latest["ema_20"] > latest["ema_50"]:
                confidence += 20
                indicators_used.append("EMA")
            if latest["rsi"] > 60:
                confidence += 15
                indicators_used.append("RSI")
            if latest["macd"] > latest["macd_signal"]:
                confidence += 15
                indicators_used.append("MACD")
            if latest["adx"] > 25:
                confidence += 10
                indicators_used.append("ADX")
            if latest["stoch_rsi"] < 0.25:
                confidence += 10
                indicators_used.append("StochRSI")
            if latest["close"] > latest["vwap"]:
                confidence += 10
                indicators_used.append("VWAP")
            if latest["mfi"] > 50:
                confidence += 10
                indicators_used.append("MFI")
            if latest["cci"] > 100:
                confidence += 10
                indicators_used.append("CCI")
            if latest["close"] > latest["ichimoku_a"] and latest["ichimoku_conversion"] > latest["ichimoku_base"]:
                confidence += 15
                indicators_used.append("Ichimoku")
            if latest["rvi"] > latest["rvi_signal"]:
                confidence += 10
                indicators_used.append("RVI")
            if latest["obv"] > prev["obv"]:
                confidence += 10
                indicators_used.append("OBV")
            if latest["hma_9"] > prev["hma_9"]:
                confidence += 10
                indicators_used.append("HMA")
            # Candle patterns
            if is_bullish_engulfing(df):
                confidence += 15
                indicators_used.append("Bullish Engulfing")
            if is_hammer(df):
                confidence += 15
                indicators_used.append("Hammer")
            if is_three_white_soldiers(df):
                confidence += 20
                indicators_used.append("Three White Soldiers")
            if is_breakout_candle(df, direction="LONG") and latest["close"] > prev["high"]:
                confidence += 15
                indicators_used.append("Breakout")
            if is_doji(df) and latest["volume"] < latest["volume_sma_20"]:
                log(f"[{symbol}] Doji detected, possible fake breakout", level='WARNING')
                return None
        else:  # SHORT
            if latest["ema_20"] < latest["ema_50"]:
                confidence += 20
                indicators_used.append("EMA")
            if latest["rsi"] < 40:
                confidence += 15
                indicators_used.append("RSI")
            if latest["macd"] < latest["macd_signal"]:
                confidence += 15
                indicators_used.append("MACD")
            if latest["adx"] > 25:
                confidence += 10
                indicators_used.append("ADX")
            if latest["stoch_rsi"] > 0.75:
                confidence += 10
                indicators_used.append("StochRSI")
            if latest["close"] < latest["vwap"]:
                confidence += 10
                indicators_used.append("VWAP")
            if latest["mfi"] < 50:
                confidence += 10
                indicators_used.append("MFI")
            if latest["cci"] < -100:
                confidence += 10
                indicators_used.append("CCI")
            if latest["close"] < latest["ichimoku_a"] and latest["ichimoku_conversion"] < latest["ichimoku_base"]:
                confidence += 15
                indicators_used.append("Ichimoku")
            if latest["rvi"] < latest["rvi_signal"]:
                confidence += 10
                indicators_used.append("RVI")
            if latest["obv"] < prev["obv"]:
                confidence += 10
                indicators_used.append("OBV")
            if latest["hma_9"] < prev["hma_9"]:
                confidence += 10
                indicators_used.append("HMA")
            # Candle patterns
            if is_bearish_engulfing(df):
                confidence += 15
                indicators_used.append("Bearish Engulfing")
            if is_shooting_star(df):
                confidence += 15
                indicators_used.append("Shooting Star")
            if is_three_black_crows(df):
                confidence += 20
                indicators_used.append("Three Black Crows")
            if is_breakout_candle(df, direction="SHORT") and latest["close"] < prev["low"]:
                confidence += 15
                indicators_used.append("Breakout")
            if is_doji(df) and latest["volume"] < latest["volume_sma_20"]:
                log(f"[{symbol}] Doji detected, possible fake breakout", level='WARNING')
                return None

        if confidence < 80:
            log(f"[{symbol}] Low confidence: {confidence}", level='WARNING')
            return None

        price = latest["close"]
        atr = latest["atr"]
        fib = calculate_fibonacci_levels(price, direction=direction)
        sr = detect_sr_levels(df)
        support = sr.get("support")
        resistance = sr.get("resistance")

        tp1 = round(fib.get("tp1", price + atr * 1.2 if direction == "LONG" else price - atr * 1.2), 4)
        tp2 = round(fib.get("tp2", price + atr * 2.0 if direction == "LONG" else price - atr * 2.0), 4)
        tp3 = round(fib.get("tp3", price + atr * 3.0 if direction == "LONG" else price - atr * 3.0), 4)
        sl = round(support if support and direction == "LONG" else resistance if resistance and direction == "SHORT" else price - atr * 0.8 if direction == "LONG" else price + atr * 0.8, 4)

        # Zero value check
        if any(v <= 0 for v in [price, tp1, tp2, tp3, sl]):
            log(f"[{symbol}] Zero value detected: price={price}, tp1={tp1}, tp2={tp2}, tp3={tp3}, sl={sl}", level='ERROR')
            return None

        tp1_possibility, tp2_possibility, tp3_possibility = calculate_dynamic_possibilities(confidence, atr, price, tp1, tp2, tp3)
        trade_type = "Normal" if confidence >= 85 else "Scalping"

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
            "leverage": 10,
            "support": support,
            "resistance": resistance,
            "tp1_possibility": tp1_possibility,
            "tp2_possibility": tp2_possibility,
            "tp3_possibility": tp3_possibility,
            "indicators_used": ", ".join(indicators_used),
            "backtest_result": None  # Will be updated by backtest
        }

        log(f"[{symbol}] Signal generated: direction={direction}, confidence={confidence}, indicators={signal['indicators_used']}")
        return signal

    except Exception as e:
        log(f"[{symbol}] Error calculating indicators: {e}", level='ERROR')
        return None

def calculate_vwap(df):
    try:
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        return (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()
    except:
        return df["close"]

def calculate_hma(series, period=9):
    try:
        wma1 = series.rolling(window=period//2).mean() * 2
        wma2 = series.rolling(window=period).mean()
        raw_hma = wma1 - wma2
        return raw_hma.rolling(window=int(np.sqrt(period))).mean()
    except:
        return series

def calculate_dynamic_possibilities(confidence, atr, price, tp1, tp2, tp3):
    try:
        volatility_factor = atr / price
        distance_tp1 = abs(tp1 - price) / price
        distance_tp2 = abs(tp2 - price) / price
        distance_tp3 = abs(tp3 - price) / price
        
        tp1_possibility = min(95, confidence + (5 if volatility_factor < 0.02 else 0) - (distance_tp1 * 100))
        tp2_possibility = min(85, confidence - (5 if volatility_factor < 0.02 else 10) - (distance_tp2 * 100))
        tp3_possibility = min(75, confidence - (15 if volatility_factor < 0.02 else 20) - (distance_tp3 * 100))
        
        return round(tp1_possibility, 2), round(tp2_possibility, 2), round(tp3_possibility, 2)
    except:
        return confidence - 5, confidence - 15, confidence - 25
