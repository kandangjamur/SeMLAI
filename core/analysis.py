import pandas as pd
import asyncio
from core.indicators import calculate_indicators
from core.candle_patterns import is_bullish_engulfing, is_bearish_engulfing, is_doji
from data.backtest import get_tp1_hit_rate
from utils.support_resistance import detect_breakout
from model.predictor import predict_confidence
from utils.logger import log

async def analyze_symbol(exchange, symbol):
    try:
        timeframes = ["15m", "1h", "4h", "1d"]
        signals = []

        for timeframe in timeframes:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=100)
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"], dtype="float32")
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

            # ہلکا والیوم چیک
            if df["volume"].mean() < 1_000:
                log(f"[{symbol}] Insufficient data or low volume for {timeframe}")
                continue

            # انڈیکیٹرز کیلکولیٹ کرو
            df = calculate_indicators(df)
            log(f"[{symbol}] Indicators calculated for {len(df)} rows in {timeframe}")

            # تازہ ترین ڈیٹا
            latest_idx = df.index[-1]
            second_latest_idx = df.index[-2]

            # سگنل انیشیلائز کرو
            direction = None
            confidence = 0.0
            indicator_count = 0

            # RSI-based signals (ہلکا تھریش ہولڈ)
            if df.loc[latest_idx, "rsi"] < 30:
                direction = "LONG"
                confidence += 30
                indicator_count += 1
            elif df.loc[latest_idx, "rsi"] > 70:
                direction = "SHORT"
                confidence += 30
                indicator_count += 1

            # MACD-based signals (ہلکا چیک)
            macd_hist = df.loc[latest_idx, "macd"] - df.loc[latest_idx, "macd_signal"]
            if df.loc[latest_idx, "macd"] > df.loc[latest_idx, "macd_signal"] and macd_hist > 0:
                if direction == "LONG" or direction is None:
                    direction = "LONG"
                    confidence += 25
                    indicator_count += 1
            elif df.loc[latest_idx, "macd"] < df.loc[latest_idx, "macd_signal"] and macd_hist < 0:
                if direction == "SHORT" or direction is None:
                    direction = "SHORT"
                    confidence += 25
                    indicator_count += 1

            # کینڈل پیٹرن (ہلکا والیوم چیک)
            if is_bullish_engulfing(df.loc[:latest_idx]) and df.loc[latest_idx, "volume"] > df.loc[second_latest_idx, "volume"] * 1.2:
                if direction == "LONG" or direction is None:
                    direction = "LONG"
                    confidence += 20
                    indicator_count += 1
            elif is_bearish_engulfing(df.loc[:latest_idx]) and df.loc[latest_idx, "volume"] > df.loc[second_latest_idx, "volume"] * 1.2:
                if direction == "SHORT" or direction is None:
                    direction = "SHORT"
                    confidence += 20
                    indicator_count += 1
            elif is_doji(df.loc[:latest_idx]):
                confidence -= 10

            # بریک آؤٹ ڈیٹیکشن
            breakout = detect_breakout(symbol, df)
            if breakout["direction"] == "up":
                if direction == "LONG" or direction is None:
                    direction = "LONG"
                    confidence += 20
                    indicator_count += 1
            elif breakout["direction"] == "down":
                if direction == "SHORT" or direction is None:
                    direction = "SHORT"
                    confidence += 20
                    indicator_count += 1

            # کم از کم 1 انڈیکیٹر
            if indicator_count < 1:
                log(f"[{symbol}] Signal rejected for {timeframe}: insufficient indicators ({indicator_count})")
                continue

            # ML-based confidence
            features = df[["rsi", "macd", "macd_signal", "close", "volume"]].iloc[-1:].copy()
            if features.dropna().empty:
                log(f"[{symbol}] Insufficient data for feature preparation", level="WARNING")
                ml_confidence = 0.5  # ڈیفالٹ کنفیڈنس
            else:
                ml_confidence = predict_confidence(symbol, df)  # df پاس کیا
                ml_confidence = ml_confidence / 100  # فیصد سے 0-1 میں تبدیل
                if ml_confidence == 0.0:
                    ml_confidence = 0.5  # صفر سے بچاؤ
            log(f"[{symbol}] ML Confidence: {ml_confidence:.2%}")
            confidence = min(confidence + ml_confidence * 50, 100)  # درست کیلکولیشن

            # ڈائریکشن چیک
            if direction not in ["LONG", "SHORT"]:
                log(f"[{symbol}] Signal rejected for {timeframe}: direction=None, confidence={confidence:.1f}")
                continue

            # TP1 امکان
            backtest_hit_rate = get_tp1_hit_rate(symbol, timeframe)
            if backtest_hit_rate == 0.7:  # ڈیفالٹ ہٹ ریٹ کی صورت میں
                log(f"[{symbol}] Using default TP1 hit rate: 0.75", level="INFO")
                backtest_hit_rate = 0.75  # بہتر ڈیفالٹ
            tp1_possibility = min(ml_confidence * 0.5 + backtest_hit_rate * 0.5, 0.95)

            # TP/SL ایڈجسٹمنٹ
            current_price = df.loc[latest_idx, "close"]
            if timeframe == "15m":
                tp_percentages = [1.015, 1.03, 1.05]  # ±1.5%, ±3%, ±5%
                sl_percentage = 0.985  # ±1.5%
            else:
                tp_percentages = [1.02, 1.05, 1.08]  # ±2%, ±5%, ±8%
                sl_percentage = 0.98  # ±2%

            if direction == "LONG":
                tp1 = current_price * tp_percentages[0]
                tp2 = current_price * tp_percentages[1]
                tp3 = current_price * tp_percentages[2]
                sl = current_price * sl_percentage
            else:  # SHORT
                tp1 = current_price / tp_percentages[0]
                tp2 = current_price / tp_percentages[1]
                tp3 = current_price / tp_percentages[2]
                sl = current_price / sl_percentage

            # سگنل بناؤ
            signal = {
                "symbol": symbol,
                "timeframe": timeframe,
                "direction": direction,
                "entry": current_price,
                "tp1": tp1,
                "tp2": tp2,
                "tp3": tp3,
                "sl": sl,
                "confidence": confidence,
                "tp1_possibility": tp1_possibility
            }

            log(f"[{symbol}] Signal for {timeframe}: {direction}, Confidence: {confidence:.2%}, TP1 Possibility: {tp1_possibility:.2%}")
            signals.append(signal)

        if not signals:
            log(f"[{symbol}] No valid signals for any timeframe", level="ERROR")
            return None

        # بہترین سگنل
        best_signal = max(signals, key=lambda x: x["confidence"])
        log(f"[{symbol}] Best signal selected: {best_signal['direction']} for {best_signal['timeframe']}, Confidence: {best_signal['confidence']:.2%}")
        return best_signal

    except Exception as e:
        log(f"[{symbol}] Error in analysis: {str(e)}", level="ERROR")
        return None
