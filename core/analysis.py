import pandas as pd
import numpy as np
from core.indicators import calculate_indicators
from utils.support_resistance import find_support_resistance, detect_breakout
from utils.logger import log
import gc

async def analyze_symbol(symbol: str, exchange, predictor, timeframe: str = "15m"):
    global predictor
    try:
        log(f"[{symbol}] Starting analysis on {timeframe}", level="INFO")
        
        if predictor is None:
            log(f"[{symbol}] Predictor not initialized", level="ERROR")
            return None

        # Fetch OHLCV data
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=50)
        log(f"[{symbol}] Fetched {len(ohlcv)} OHLCV rows", level="INFO")
        
        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
            dtype="float32"
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        
        # Calculate indicators
        df = calculate_indicators(df)
        if df is None or df.empty:
            log(f"[{symbol}] Failed to calculate indicators", level="WARNING")
            return None
        
        # Calculate support/resistance
        df = find_support_resistance(df)
        if df is None or df.empty or 'support' not in df.columns or 'resistance' not in df.columns:
            log(f"[{symbol}] Failed to calculate support/resistance", level="ERROR")
            df['support'] = df['low'].astype('float32')
            df['resistance'] = df['high'].astype('float32')
        
        # Set dynamic TP hit rates based on predictor confidence
        signal = await predictor.predict_signal(symbol, df, timeframe)
        if signal is None:
            log(f"[{symbol}] No valid signal from predictor", level="INFO")
            # Check for breakout as fallback
            breakout = detect_breakout(symbol, df)
            if breakout["is_breakout"]:
                direction = "LONG" if breakout["direction"] == "up" else "SHORT"
                confidence = 90.0  # Fixed confidence for breakout
                tp1_possibility = 0.85
                tp2_possibility = 0.65
                tp3_possibility = 0.45
            else:
                return None
        else:
            direction = signal["direction"]
            confidence = signal["confidence"]
            # Dynamic TP possibilities based on confidence
            tp1_possibility = min(0.75 + (confidence / 100 - 0.65) * 0.15, 0.90)
            tp2_possibility = min(0.50 + (confidence / 100 - 0.65) * 0.20, 0.75)
            tp3_possibility = min(0.25 + (confidence / 100 - 0.65) * 0.25, 0.60)

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
            "tp1_possibility": round(tp1_possibility, 2),
            "tp2_possibility": round(tp2_possibility, 2),
            "tp3_possibility": round(tp3_possibility, 2)
        }

        log(f"[{symbol}] Signal generated - Direction: {direction}, Confidence: {confidence:.2f}%, TP1: {tp1_possibility:.2f}, TP2: {tp2_possibility:.2f}, TP3: {tp3_possibility:.2f}", level="INFO")
        return result
    except Exception as e:
        log(f"[{symbol}] Error in analysis: {str(e)}", level="ERROR")
        return None
    finally:
        if 'df' in locals():
            del df
        gc.collect()
