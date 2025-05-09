import pandas as pd
import asyncio
from core.indicators import calculate_indicators
from core.candle_patterns import is_bullish_engulfing, is_bearish_engulfing, is_doji
from data.backtest import get_tp1_hit_rate
from utils.support_resistance import detect_breakout
from model.predictor import predict_confidence
from utils.logger import log

async def fetch_ohlcv_safe(exchange, symbol, timeframe, retries=3):
    for _ in range(retries):
        try:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=100)
            if ohlcv and len(ohlcv) >= 20:
                return ohlcv
        except Exception as e:
            await asyncio.sleep(0.5)
    return None

async def analyze_symbol(exchange, symbol):
    try:
        timeframes = ["15m", "1h", "4h", "1d"]
        signals = []
        timeframe_directions = {}

        for timeframe in timeframes:
            ohlcv = await fetch_ohlcv_safe(exchange, symbol, timeframe)
            if not ohlcv:
                log(f"[{symbol}] Failed to fetch OHLCV or insufficient data for {timeframe}", level="ERROR")
                continue

            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"], dtype="float32")
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

            if df["volume"].mean() < 50_000 or df["volume"].max() == 0:
                log(f"[{symbol}] Low or invalid volume in {timeframe}", level="WARNING")
                continue

            df = calculate_indicators(df)
            if df.isnull().values.any():
                log(f"[{symbol}] NaN values found in indicators for {timeframe}", level="WARNING")
                continue

            latest_idx = df.index[-1]
            second_latest_idx = df.index[-2]

            direction = None
            confidence = 0.0
            indicator_count = 0

            # RSI
            if df.loc[latest_idx, "rsi"] < 25:
                direction = "LONG"
                confidence += 30
                indicator_count += 1
            elif df.loc[latest_idx, "rsi"] > 75:
                direction = "SHORT"
                confidence += 30
                indicator_count += 1

            # MACD crossover
            macd_hist = df.loc[latest_idx, "macd"] - df.loc[latest_idx, "macd_signal"]
            macd_cross_up = df.loc[latest_idx, "macd"] > df.loc[latest_idx, "macd_signal"] and df.loc[second_latest_idx, "macd"] <= df.loc[second_latest_idx, "macd_signal"]
            macd_cross_down = df.loc[latest_idx, "macd"] < df.loc[latest_idx, "macd_signal"] and df.loc[second_latest_idx, "macd"] >= df.loc[second_latest_idx, "macd_signal"]

            if macd_cross_up and macd_hist > 0:
                if direction in [None, "LONG"]:
                    direction = "LONG"
                    confidence += 25
                    indicator_count += 1
            elif macd_cross_down and macd_hist < 0:
                if direction in [None, "SHORT"]:
                    direction = "SHORT"
                    confidence += 25
                    indicator_count += 1

            # Candlestick pattern
            if is_bullish_engulfing(df.loc[:latest_idx]) and df.loc[latest_idx, "volume"] > df.loc[second_latest_idx, "volume"] * 1.2:
                if direction in [None, "LONG"]:
                    direction = "LONG"
                    confidence += 20
                    indicator_count += 1
            elif is_bearish_engulfing(df.loc[:latest_idx]) and df.loc[latest_idx, "volume"] > df.loc[second_latest_idx, "volume"] * 1.2:
                if direction in [None, "SHORT"]:
                    direction = "SHORT"
                    confidence += 20
                    indicator_count += 1
            elif is_doji(df.loc[:latest_idx]):
                confidence -= 15

            # Breakout
            breakout = detect_breakout(df)
            if breakout == "up" and direction in [None, "LONG"]:
                direction = "LONG"
                confidence += 20
                indicator_count += 1
            elif breakout == "down" and direction in [None, "SHORT"]:
                direction = "SHORT"
                confidence += 20
                indicator_count += 1

            if indicator_count < 2:
                log(f"[{symbol}] Skipped {timeframe}: insufficient indicators ({indicator_count})")
                continue

            # ML Prediction
            features = df[["rsi", "macd", "macd_signal", "close", "volume"]].iloc[-1:].copy()
            ml_conf = await predict_confidence(symbol, features)
            log(f"[{symbol}] ML confidence for {timeframe}: {ml_conf:.2%}")
            confidence = min(confidence + ml_conf * 0.5, 100)

            if direction not in ["LONG", "SHORT"]:
                log(f"[{symbol}] Skipped {timeframe}: direction None")
                continue

            timeframe_directions[timeframe] = direction
            backtest_hit_rate = get_tp1_hit_rate(symbol, timeframe)
            tp1_possibility = min(ml_conf * 0.5 + backtest_hit_rate * 0.5, 0.95)

            current_price = df.loc[latest_idx, "close"]
            if timeframe == "15m":
                tp_percentages = [1.015, 1.03, 1.05]
                sl_percentage = 0.985
            else:
                tp_percentages = [1.02, 1.05, 1.08]
                sl_percentage = 0.98

            if direction == "LONG":
                tp1 = round(current_price * tp_percentages[0], 6)
                tp2 = round(current_price * tp_percentages[1], 6)
                tp3 = round(current_price * tp_percentages[2], 6)
                sl = round(current_price * sl_percentage, 6)
            else:
                tp1 = round(current_price / tp_percentages[0], 6)
                tp2 = round(current_price / tp_percentages[1], 6)
                tp3 = round(current_price / tp_percentages[2], 6)
                sl = round(current_price / sl_percentage, 6)

            signal = {
                "symbol": symbol,
                "timeframe": timeframe,
                "direction": direction,
                "entry": current_price,
                "tp1": tp1,
                "tp2": tp2,
                "tp3": tp3,
                "sl": sl,
                "
