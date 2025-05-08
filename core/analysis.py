import pandas as pd
import asyncio
from core.indicators import calculate_indicators
from core.candle_patterns import is_bullish_engulfing, is_bearish_engulfing, is_doji
from utils.support_resistance import detect_breakout
from utils.fibonacci import calculate_fibonacci_levels
from model.predictor import predict_confidence
from core.news_sentiment import fetch_sentiment, adjust_confidence
from utils.logger import log

async def analyze_symbol(exchange, symbol):
    try:
        timeframes = ["15m", "1h", "4h", "1d"]
        signals = []

        for timeframe in timeframes:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=100)
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"], dtype="float32")
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

            # Relaxed checks
            if len(df) < 30 or df["volume"].mean() < 5_000:
                log(f"[{symbol}] Insufficient data or low volume for {timeframe}", level='WARNING')
                continue

            df = calculate_indicators(df)
            if df is None:
                log(f"[{symbol}] No indicators for {timeframe}", level='WARNING')
                continue

            confidence = 50.0
            direction = None

            # Rule-based signals
            if df["rsi"].iloc[-1] < 30:
                direction = "LONG"
                confidence += 25  # Increased weight for RSI
            elif df["rsi"].iloc[-1] > 70:
                direction = "SHORT"
                confidence += 25

            if df["macd"].iloc[-1] > df["macd_signal"].iloc[-1] and df["macd"].iloc[-2] <= df["macd_signal"].iloc[-2]:
                confidence += 10
            elif df["macd"].iloc[-1] < df["macd_signal"].iloc[-1] and df["macd"].iloc[-2] >= df["macd_signal"].iloc[-2]:
                confidence += 10

            if df["close"].iloc[-1] > df["bb_upper"].iloc[-1]:
                confidence -= 10
            elif df["close"].iloc[-1] < df["bb_lower"].iloc[-1]:
                confidence -= 10

            # Candle patterns
            if is_bullish_engulfing(df.iloc[-2:]):
                confidence += 10
                direction = "LONG"
            elif is_bearish_engulfing(df.iloc[-2:]):
                confidence += 10
                direction = "SHORT"
            elif is_doji(df.iloc[-1:]):
                confidence -= 5

            # Breakout detection
            breakout = detect_breakout(symbol, df)
            if breakout["is_breakout"]:
                confidence += 15
                direction = "LONG" if breakout["direction"] == "up" else "SHORT"

            # ML confidence (optional)
            try:
                ml_confidence = predict_confidence(symbol, df)
                confidence = (confidence + ml_confidence) / 2
            except Exception as e:
                log(f"[{symbol}] ML confidence failed: {e}", level='WARNING')

            # Sentiment adjustment (optional)
            try:
                sentiment_score = fetch_sentiment(symbol)  # Removed 'await' since fetch_sentiment is not async
                confidence = adjust_confidence(confidence, sentiment_score)  # Adjusted to match function signature
            except Exception as e:
                log(f"[{symbol}] Sentiment analysis failed: {e}", level='WARNING')

            # Fibonacci levels for TP/SL
            fib_levels = calculate_fibonacci_levels(df)
            if fib_levels is None or fib_levels.empty:
                log(f"[{symbol}] No Fibonacci levels for {timeframe}", level='WARNING')
                continue

            # Use correct DataFrame column access for Fibonacci levels
            try:
                tp1 = fib_levels["0.382"].iloc[-1] if direction == "LONG" else fib_levels["-0.382"].iloc[-1]
                tp2 = fib_levels["0.618"].iloc[-1] if direction == "LONG" else fib_levels["-0.618"].iloc[-1]
                tp3 = fib_levels["1.0"].iloc[-1] if direction == "LONG" else fib_levels["-1.0"].iloc[-1]
                sl = fib_levels["-0.236"].iloc[-1] if direction == "LONG" else fib_levels["0.236"].iloc[-1]
            except KeyError as e:
                log(f"[{symbol}] Error accessing Fibonacci levels: {e}", level='ERROR')
                continue

            signal = {
                "symbol": symbol,
                "timeframe": timeframe,
                "direction": direction,
                "price": df["close"].iloc[-1],
                "confidence": min(95, round(confidence, 2)),
                "tp1": tp1,
                "tp2": tp2,
                "tp3": tp3,
                "sl": sl,
                "tp1_possibility": 80 if confidence >= 60 else 50,
                "timestamp": df["timestamp"].iloc[-1]
            }

            if signal["confidence"] >= 60 and signal["tp1_possibility"] >= 80:
                signals.append(signal)
                log(f"[{symbol}] Signal for {timeframe}: {signal['direction']}, Confidence: {signal['confidence']}%")

        if not signals:
            log(f"[{symbol}] No valid signals for any timeframe", level='ERROR')
            return None

        best_signal = max(signals, key=lambda x: x["confidence"])
        return best_signal
    except Exception as e:
        log(f"[{symbol}] Error in analysis: {e}", level='ERROR')
        return None
