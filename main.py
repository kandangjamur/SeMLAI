import pandas as pd
import asyncio
from fastapi import FastAPI, BackgroundTasks
from core.indicators import calculate_indicators
from core.candle_patterns import is_bullish_engulfing, is_bearish_engulfing, is_doji
from data.backtest import get_tp1_hit_rate
from utils.support_resistance import detect_breakout
from model.predictor import predict_confidence
from utils.logger import log
import logging
from logging.handlers import RotatingFileHandler

# FastAPI app initialization
app = FastAPI()

# Setting up logging
logger = logging.getLogger()
handler = RotatingFileHandler('app.log', maxBytes=5 * 1024 * 1024, backupCount=3)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

@app.get("/")
async def read_root():
    return {"message": "Crypto Signal Bot Running!"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

async def fetch_ohlcv_safe(exchange, symbol, timeframe, retries=3):
    for _ in range(retries):
        try:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=100)
            if ohlcv and len(ohlcv) >= 20:
                return ohlcv
        except Exception as e:
            log(f"Error fetching OHLCV for {symbol} on {timeframe}: {e}", level="ERROR")
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
            try:
                features = df[["rsi", "macd", "macd_signal", "close", "volume"]].iloc[-1:].copy()
                ml_conf = await predict_confidence(symbol, features)
            except Exception as e:
                log(f"[{symbol}] ML prediction failed: {e}", level="ERROR")
                ml_conf = 0  # Fallback to 0 if prediction fails

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
                "confidence": round(confidence, 2),
                "tp1_possibility": round(tp1_possibility, 4),
            }

            log(f"[{symbol}] Signal {timeframe}: {direction}, Confidence: {confidence:.2f}%, TP1 Possibility: {tp1_possibility:.2%}")
            signals.append(signal)

        if not signals:
            log(f"[{symbol}] No valid signals found", level="ERROR")
            return None

        # Multi-timeframe agreement filter
        valid_signals = []
        for sig in signals:
            tf = sig["timeframe"]
            dir_ = sig["direction"]
            others = [k for k in timeframe_directions if k != tf]
            agreement = any(timeframe_directions.get(o) == dir_ for o in others)
            if agreement:
                valid_signals.append(sig)
            else:
                log(f"[{symbol}] Rejected {tf}: no multi-timeframe agreement")

        if not valid_signals:
            log(f"[{symbol}] No signals with multi-timeframe agreement", level="ERROR")
            return None

        best = max(valid_signals, key=lambda x: x["confidence"])
        log(f"[{symbol}] Final signal: {best['direction']} in {best['timeframe']}, Confidence: {best['confidence']:.2f}%")
        return best

    except Exception as e:
        log(f"[{symbol}] Fatal error: {str(e)}", level="ERROR")
        return None

# Run the FastAPI app (if running in a local or production environment)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=4)  # Added 4 workers for better concurrency
