import logging
import pandas as pd
from typing import Optional, Dict
from utils.indicators import calculate_indicators
from utils.support_resistance import detect_breakout, calculate_support_resistance
from predictors.random_forest import RandomForestPredictor
from datetime import datetime

async def analyze_symbol(symbol: str, df: pd.DataFrame, timeframe: str, predictor: RandomForestPredictor) -> Optional[Dict]:
    log = logging.getLogger("crypto-signal-bot")
    
    log.info(f"[{symbol}] Starting analysis on {timeframe}")
    
    try:
        # Calculate technical indicators
        df = calculate_indicators(df)
        log.info(f"[{symbol}] Indicators calculated: RSI, MACD, ATR, Volume, Bollinger Bands, Volume SMA 20")
        
        # Calculate support and resistance
        support_resistance = calculate_support_resistance(symbol, df)
        log.info(f"[{symbol}] Support/Resistance calculated: Last support={support_resistance['support']:.2f}, resistance={support_resistance['resistance']:.2f}")
        
        # Prepare features for prediction
        features = {
            'rsi': df['rsi'].iloc[-1],
            'macd': df['macd'].iloc[-1],
            'macd_signal': df['macd_signal'].iloc[-1],
            'bb_upper': df['bb_upper'].iloc[-1],
            'bb_lower': df['bb_lower'].iloc[-1],
            'atr': df['atr'].iloc[-1],
            'volume': df['volume'].iloc[-1],
            'volume_sma_20': df['volume_sma_20'].iloc[-1],
            'bullish_engulfing': df['bullish_engulfing'].iloc[-1],
            'bearish_engulfing': df['bearish_engulfing'].iloc[-1],
            'doji': df['doji'].iloc[-1],
            'hammer': df['hammer'].iloc[-1],
            'shooting_star': df['shooting_star'].iloc[-1],
            'three_white_soldiers': df['three_white_soldiers'].iloc[-1],
            'three_black_crows': df['three_black_crows'].iloc[-1],
        }
        log.info(f"[{symbol}] Features prepared: {features}")
        
        # Get signal from predictor
        signal = await predictor.predict_signal(symbol, df, timeframe)
        
        if signal is None:
            log.info(f"[{symbol}] No valid signal from predictor")
            # Check for breakout as fallback
            breakout = detect_breakout(symbol, df)
            if breakout["is_breakout"]:
                direction = "LONG" if breakout["direction"] == "up" else "SHORT"
                confidence = 90.0  # Fixed confidence for breakout
                tp1_possibility = 0.85  # Static for breakout
                tp2_possibility = 0.65
                tp3_possibility = 0.45
            else:
                return None
        else:
            direction = signal["direction"]
            confidence = signal["confidence"]
            
            # Dynamic TP possibilities based on confidence (threshold raised to 75%)
            tp1_possibility = min(0.80 + (confidence / 100 - 0.75) * 0.15, 0.95)
            tp2_possibility = min(0.60 + (confidence / 100 - 0.75) * 0.20, 0.80)
            tp3_possibility = min(0.40 + (confidence / 100 - 0.75) * 0.25, 0.65)
            
            # Skip if confidence is too low
            if confidence < 75.0:
                log.info(f"[{symbol}] Low confidence: {confidence:.2f}%")
                return None
        
        # Log signal
        log.info(f"[{symbol}] Signal generated - Direction: {direction}, Confidence: {confidence:.2f}%, TP1: {tp1_possibility:.2f}, TP2: {tp2_possibility:.2f}, TP3: {tp3_possibility:.2f}")
        
        # Return signal data
        return {
            "symbol": symbol,
            "direction": direction,
            "confidence": confidence,
            "tp1_possibility": tp1_possibility,
            "tp2_possibility": tp2_possibility,
            "tp3_possibility": tp3_possibility,
            "support": support_resistance["support"],
            "resistance": support_resistance["resistance"],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        log.error(f"[{symbol}] Error during analysis: {str(e)}")
        return None
