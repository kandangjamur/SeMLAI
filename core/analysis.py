import pandas as pd
import asyncio
from core.indicators import calculate_indicators
from core.candle_patterns import is_bullish_engulfing, is_bearish_engulfing, is_doji
from utils.support_resistance import detect_breakout
from model.predictor import predict_confidence
from utils.logger import log

async def analyze_symbol(exchange, symbol):
    try:
        timeframes = ["15m", "1h", "4h", "1d"]
        signals = []
        timeframe_directions = {}

        for timeframe in timeframes:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=100)
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"], dtype="float32")
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

            # سخت والیوم چیک
            if len(df) < 20 or df["volume"].mean() < 50_000:
                log(f"[{symbol}] Insufficient data or low volume for {timeframe}")
                continue

            # انڈیکیٹرز کیلکولیٹ کرو
            df = calculate_indicators(df)
            log(f"[{symbol}] Indicators calculated for {len(df)} rows in {timeframe}")

            # تازہ ترین کینڈل ڈیٹا
            latest = df.iloc[-1]
            second_latest = df.iloc[-2]

            # سگنل انیشیلائز کرو
            direction = None
            confidence = 0.0
            indicator_count = 0

            # RSI-based signals (سخت تھریشولڈز)
            if latest["rsi"] < 25:
                direction = "LONG"
                confidence += 30
                indicator_count += 1
            elif latest["rsi"] > 75:
                direction = "SHORT"
                confidence += 30
                indicator_count += 1

            # MACD-based signals (ہسٹوگرام کنفرمیشن کے ساتھ)
            macd_hist = latest["macd"] - latest["macd_signal"]
            if latest["macd"] > latest["macd_signal"] and second_latest["macd"] <= second_latest["macd_signal"] and macd_hist > 0:
                if direction == "LONG" or direction is None:
                    direction = "LONG"
                    confidence += 25
                    indicator_count += 1
            elif latest["macd"] < latest["macd_signal"] and second_latest["macd"] >= second_latest["macd_signal"] and macd_hist < 0:
                if direction == "SHORT" or direction is None:
                    direction = "SHORT"
                    confidence += 25
                    indicator_count += 1

            # کینڈل پیٹرن (والیوم کنفرمیشن کے ساتھ)
            if is_bullish_engulfing(second_latest, latest) and latest["volume"] > second_latest["volume"] * 1.2:
                if direction == "LONG" or direction is None:
                    direction = "LONG"
                    confidence += 20
                    indicator_count += 1
            elif is_bearish_engulfing(second_latest, latest) and latest["volume"] > second_latest["volume"] * 1.2:
                if direction == "SHORT" or direction is None:
                    direction = "SHORT"
                    confidence += 20
                    indicator_count += 1
            elif is_doji(latest):
                confidence -= 15  # غیر یقینی کے لیے کنفیڈنس کم کرو

            # بریک آؤٹ ڈیٹیکشن
            breakout = detect_breakout(df)
            if breakout == "up":
                if direction == "LONG" or direction is None:
                    direction = "LONG"
                    confidence += 20
                    indicator_count += 1
            elif breakout == "down":
                if direction == "SHORT" or direction is None:
                    direction = "SHORT"
                    confidence += 20
                    indicator_count += 1

            # کم از کم 2 انڈیکیٹرز کی ضرورت
            if indicator_count < 2:
                log(f"[{symbol}] Signal rejected for {timeframe}: insufficient indicators ({indicator_count})")
                continue

            # ML-based confidence
            # فیچر نیمز کے ساتھ ڈیٹا تیار کرو تاکہ sklearn وارننگ نہ آئے
            features = df[["rsi", "macd", "macd_signal", "close", "volume"]].iloc[-1:].copy()
            ml_confidence = await predict_confidence(features)
            log(f"[{symbol}] ML Confidence: {ml_confidence:.2%}")
            confidence = min(confidence + ml_confidence * 50, 100)  # ML کا وزن کم کیا

            # ڈائریکشن چیک
            if direction not in ["LONG", "SHORT"]:
                log(f"[{symbol}] Signal rejected for {timeframe}: direction=None, confidence={confidence:.1f}")
                continue

            # ملٹی ٹائم فریم ایگریمنٹ کے لیے ڈائریکشن سٹور کرو
            timeframe_directions[timeframe] = direction

            # TP1 امکان کیلکولیٹ کرو (ML کنفیڈنس + ڈمی تاریخی ہٹ ریٹ)
            historical_hit_rate = 0.7  # فرضی، اصل میں بیک ٹیسٹ ڈیٹا سے لے سکتے ہو
            tp1_possibility = min(ml_confidence + historical_hit_rate - 0.2, 0.95)

            # ٹائم فریم کی بنیاد پر TP/SL ایڈجسٹ کرو
            current_price = latest["close"]
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

        # ملٹی ٹائم فریم ایگریمنٹ چیک
        valid_signals = []
        for signal in signals:
            tf = signal["timeframe"]
            direction = signal["direction"]
            # چیک کرو کہ کم از کم ایک اور ٹائم فریم میں وہی ڈائریکشن ہو
            other_tfs = [t for t in timeframe_directions if t != tf]
            has_agreement = any(timeframe_directions.get(other_tf) == direction for other_tf in other_tfs)
            if has_agreement:
                valid_signals.append(signal)
            else:
                log(f"[{symbol}] Signal rejected for {tf}: no multi-timeframe agreement")

        if not valid_signals:
            log(f"[{symbol}] No signals with multi-timeframe agreement", level="ERROR")
            return None

        # بہترین سگنل چنو (سب سے زیادہ کنفیڈنس)
        best_signal = max(valid_signals, key=lambda x: x["confidence"])
        log(f"[{symbol}] Best signal selected: {best_signal['direction']} for {best_signal['timeframe']}, Confidence: {best_signal['confidence']:.2%}")
        return best_signal

    except Exception as e:
        log(f"[{symbol}] Error in analysis: {str(e)}", level="ERROR")
        return None
