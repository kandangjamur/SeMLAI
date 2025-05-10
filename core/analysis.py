import ccxt.async_support as ccxt
import pandas as pd
from core.indicators import calculate_indicators
from data.backtest import get_tp_hit_rates
from model.predictor import SignalPredictor
from utils.support_resistance import detect_breakout
from utils.logger import log
import numpy as np
import asyncio
import gc

# Global predictor instance
predictor = None

async def initialize_predictor():
    global predictor
    if predictor is None:
        try:
            predictor = SignalPredictor()
            log("Random Forest model loaded successfully")
        except Exception as e:
            log(f"Error loading Random Forest model: {e}", level="ERROR")
            raise

async def analyze_symbol(exchange: ccxt.binance, symbol: str, timeframe: str = "15m"):
    global predictor
    try:
        log(f"[{symbol}] Starting analysis on {timeframe}")
        
        if predictor is None:
            log(f"[{symbol}] Predictor not initialized", level="ERROR")
            return None

        # Fetch OHLCV data
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=50)  # Increased for indicators
        log(f"[{symbol}] Fetched {len(ohlcv)} OHLCV rows")
        
        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
            dtype="float16"
        )
        
        # Calculate indicators
        df = calculate_indicators(df)
        if df is None:
            log(f"[{symbol}] Failed to calculate indicators", level="WARNING")
            return None
        
        # Get TP hit rates
        try:
            tp1_possibility, tp2_possibility, tp3_possibility = await get_tp_hit_rates(symbol, timeframe)
        except Exception as e:
            log(f"[{symbol}] Error getting TP hit rates: {e}", level="ERROR")
            return None
        log(f"[{symbol}] TP hit rates - TP1: {tp1_possibility:.2%}, TP2: {tp2_possibility:.2%}, TP3: {tp3_possibility:.2%}")

        # Detect breakout
        breakout = detect_breakout(symbol, df)
        if breakout["is_breakout"]:
            direction = "LONG" if breakout["direction"] == "up" else "SHORT"
            confidence = 0.9
        else:
            # Predict signal
            try:
                signal = await predictor.predict_signal(symbol, df, timeframe)
                if signal is None:
                    log(f"[{symbol}] No valid signal from predictor", level="INFO")
                    return None
                direction = signal["direction"]
                confidence = signal["confidence"]
            except Exception as e:
                log(f"[{symbol}] Error predicting signal: {e}", level="ERROR")
                return None

        current_price = df["close"].iloc[-1]
        atr = df["atr"].iloc[-1]
        
        # Calculate TP and SL levels
        if direction == "LONG":
            tp1 = current_price + (0.15 * atr)
            tp2 = current_price + (0.3 * atr)
            tp3 = current_price + (0.45 * atr)
            sl = current_price - (1.2 * atr)
        else:  # SHORT
            tp1 = current_price - (0.15 * atr)
            tp2 = current_price - (0.3 * atr)
            tp3 = current_price - (0.45 * atr)
            sl = current_price + (1.2 * atr)

        # Prepare result
        result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": direction,
            "entry": current_price,
            "tp1": round(tp1, 4),
            "tp2": round(tp2, 4),
            "tp3": round(tp3, 4),
            "sl": round(sl, 4),
            "confidence": confidence,
            "tp1_possibility": tp1_possibility,
            "tp2_possibility": tp2_possibility,
            "tp3_possibility": tp3_possibility
        }

        log(f"[{symbol}] Signal generated - Direction: {direction}, Confidence: {confidence:.2%}")
        return result

    except Exception as e:
        log(f"[{symbol}] Error in analysis: {e}", level="ERROR")
        return None
    finally:
        if 'df' in locals():
            del df
        gc.collect()
