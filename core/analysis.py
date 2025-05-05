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

            if len(df) < 50 or df["volume"].mean() < 50_000:
                log(f"[{symbol}] Insufficient data or low volume for {timeframe}", level='WARNING')
                continue

            df = calculate_indicators(df)
            if df is None:
                log(f"[{symbol}] No indicators for {timeframe}", level='WARNING')
                continue

            confidence = 50.0
            direction = None

            # Rule-based signals
            if df["rsi"].iloc[-1] < 30 and df["stoch_rsi"].iloc[-1] < 20:
                direction = "LONG"
                confidence += 20
            elif df["rsi"].iloc[-1] > 70 and df["stoch_rsi"].iloc[-1] > 80:
                direction = "SHORT"
                confidence += 20

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

            # ML confidence
            ml_confidence = predict_confidence(symbol, df)
            confidence = (confidence + ml_confidence) / 2

            # Sentiment adjustment
            sentiment_score = await fetch_sentiment(symbol)
            confidence = adjust_confidence(symbol, confidence, sentiment_score)

            # Fibonacci levels for TP/SL
            fib_levels = calculate_fibonacci_levels(df)
            tp1 = fib_levels["0.382"] if direction == "LONG" else fib_levels["-0.382"]
            tp2 = fib_levels["0.618"] if direction == "LONG" else fib_levels["-0.618"]
            tp3 = fib_levels["1.0"] if direction == "LONG" else fib_levels["-1.0"]
            sl = fib_levels["-0.236"] if direction == "LONG" else fib_levels["0.236"]

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
                "tp1_chance": 75 if confidence >= 80 else 50,
                "timestamp": df["timestamp"].iloc[-1]
            }

            if signal["confidence"] >= 80 and signal["tp1_chance"] >= 75:
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
