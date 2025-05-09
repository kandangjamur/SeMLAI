import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from core.indicators import calculate_indicators
from model.predictor import SignalPredictor
from data.backtest import get_tp_hit_rates
from utils.logger import log

async def analyze_symbol(exchange: ccxt.Exchange, symbol: str, timeframe: str = "15m"):
    """
    Analyze a symbol and generate trading signal.

    Args:
        exchange (ccxt.Exchange): Exchange instance
        symbol (str): Symbol to analyze (e.g., BTC/USDT)
        timeframe (str): Timeframe for analysis (default: 15m)

    Returns:
        dict: Trading signal details or None if no valid signal
    """
    try:
        log(f"[{symbol}] Starting analysis on {timeframe}")
        
        # Fetch OHLCV data
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=100)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"], dtype="float32")
        log(f"[{symbol}] Fetched {len(df)} OHLCV rows")

        # Calculate indicators
        df = calculate_indicators(df)
        if df is None or len(df) < 30:
            log(f"[{symbol}] Insufficient data after indicators", level="WARNING")
            return None

        # Initialize predictor
        predictor = SignalPredictor()
        
        # Get TP hit rates
        tp1_hit_rate, tp2_hit_rate, tp3_hit_rate = await get_tp_hit_rates(symbol, timeframe)
        log(f"[{symbol}] TP hit rates - TP1: {tp1_hit_rate:.2%}, TP2: {tp2_hit_rate:.2%}, TP3: {tp3_hit_rate:.2%}")

        # Predict signal
        signal = predictor.predict_signal(symbol, df, timeframe)
        if not signal:
            log(f"[{symbol}] No valid signal generated")
            return None

        # Add TP hit rates to signal
        signal["tp1_possibility"] = tp1_hit_rate
        signal["tp2_possibility"] = tp2_hit_rate
        signal["tp3_possibility"] = tp3_hit_rate

        # Validate signal
        if signal["confidence"] < 75 or signal["tp1_possibility"] < 0.75:
            log(f"[{symbol}] Signal rejected - Confidence: {signal['confidence']:.2f}%, TP1 Possibility: {signal['tp1_possibility']*100:.2f}%")
            return None

        log(f"[{symbol}] Valid signal - Direction: {signal['direction']}, Confidence: {signal['confidence']:.2f}%")
        return signal

    except Exception as e:
        log(f"[{symbol}] Error in analysis: {str(e)}", level="ERROR")
        return None
