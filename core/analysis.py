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

        for timeframe in timeframes:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=100)
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"], dtype="float32")
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

            # Relaxed data checks to allow more pairs
            if len(df) < 20 or df["volume"].mean() < 5_000:
                log(f"[{symbol}] Insufficient data or low volume for {timeframe}")
                continue

            # Calculate indicators (RSI, MACD, etc.)
            df = calculate_indicators(df)
            log(f"Indicators calculated for {len(df)} rows")

            # Get the latest candle data
            latest = df.iloc[-1]
            second_latest = df.iloc[-2]

            # Initialize signal
            direction = None
            confidence = 0.0

            # RSI-based signals
            if latest["rsi"] < 30:
                direction = "LONG"
                confidence += 30
            elif latest["rsi"] > 70:
                direction = "SHORT"
                confidence += 30

            # MACD-based signals
            if latest["macd"] > latest["macd_signal"] and second_latest["macd"] <= second_latest["macd_signal"]:
                direction = "LONG"
                confidence += 20
            elif latest["macd"] < latest["macd_signal"] and second_latest["macd"] >= second_latest["macd_signal"]:
                direction = "SHORT"
                confidence += 20

            # Candle pattern signals
            if is_bullish_engulfing(second_latest, latest):
                direction = "LONG"
                confidence += 15
            elif is_bearish_engulfing(second_latest, latest):
                direction = "SHORT"
                confidence += 15
            elif is_doji(latest):
                confidence -= 10  # Reduce confidence for indecision

            # Breakout detection
            breakout = detect_breakout(df)
            if breakout == "up":
                direction = "LONG"
                confidence += 15
            elif breakout == "down":
                direction = "SHORT"
                confidence += 15

            # ML-based confidence
            ml_confidence = await predict_confidence(df)
            log(f"[{symbol}] ML Confidence: {ml_confidence:.2%}")
            confidence = min(confidence + ml_confidence * 100, 100)

            # Ensure direction is set
            if direction not in ["LONG", "SHORT"]:
                log(f"[{symbol}] Signal rejected for {timeframe}: direction=None, confidence={confidence:.1f}")
                continue

            # Calculate fixed percentage TP/SL
            current_price = latest["close"]
            if direction == "LONG":
                tp1 = current_price * 1.02  # +2%
                tp2 = current_price * 1.05  # +5%
                tp3 = current_price * 1.08  # +8%
                sl = current_price * 0.98   # -2%
            else:  # SHORT
                tp1 = current_price * 0.98  # -2%
                tp2 = current_price * 0.95  # -5%
                tp3 = current_price * 0.92  # -8%
                sl = current_price * 1.02   # +2%

            # Create signal
            signal = {
                "symbol": symbol,
                "timeframe": timeframe,
                "direction": direction,
                "entry": current_price,
                "tp1": tp1,
                "tp2": tp2,
                "tp3": tp3,
                "sl": sl,
                "confidence": confidence
            }

            log(f"[{symbol}] Signal for {timeframe}: {direction}, Confidence: {confidence:.2%}")
            signals.append(signal)

        if not signals:
            log(f"[{symbol}] No valid signals for any timeframe", level="ERROR")
            return None

        # Select the best signal (highest confidence)
        best_signal = max(signals, key=lambda x: x["confidence"])
        log(f"[{symbol}] Best signal selected: {best_signal['direction']} for {best_signal['timeframe']}, Confidence: {best_signal['confidence']:.2%}")
        return best_signal

    except Exception as e:
        log(f"[{symbol}] Error in analysis: {str(e)}", level="ERROR")
        return None
