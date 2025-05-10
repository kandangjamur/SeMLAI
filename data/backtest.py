import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from utils.logger import log
import asyncio
from core.indicators import calculate_indicators
from core.candle_patterns import (
    is_bullish_engulfing, is_bearish_engulfing, is_doji, is_hammer, is_shooting_star,
    is_three_white_soldiers, is_three_black_crows
)
import gc

async def get_tp_hit_rates(symbol: str, timeframe: str):
    try:
        # Check if backtest data exists
        backtest_file = "logs/signals_log.csv"
        if pd.io.common.file_exists(backtest_file):
            df = pd.read_csv(backtest_file)
            df = df[df["symbol"] == symbol]
            
            if len(df) >= 5:
                tp1_hits = 0
                tp2_hits = 0
                tp3_hits = 0
                total_trades = len(df)
                
                for _, row in df.iterrows():
                    if row["prediction"] == "LONG":
                        if row["price"] <= row["tp1"]:
                            tp1_hits += 1
                        if row["price"] <= row["tp2"]:
                            tp2_hits += 1
                        if row["price"] <= row["tp3"]:
                            tp3_hits += 1
                    else:  # SHORT
                        if row["price"] >= row["tp1"]:
                            tp1_hits += 1
                        if row["price"] >= row["tp2"]:
                            tp2_hits += 1
                        if row["price"] >= row["tp3"]:
                            tp3_hits += 1
                
                tp1_rate = min(tp1_hits / total_trades if total_trades > 0 else 0.0, 0.95)
                tp2_rate = min(tp2_hits / total_trades if total_trades > 0 else 0.0, 0.85)
                tp3_rate = min(tp3_hits / total_trades if total_trades > 0 else 0.0, 0.75)
                
                log(f"[{symbol}] Backtest TP1 hit rate: {tp1_rate:.2%}, TP2: {tp2_rate:.2%}, TP3: {tp3_rate:.2%}")
                return tp1_rate, tp2_rate, tp3_rate

        # Fetch historical data
        log(f"[{symbol}] Insufficient backtest data, fetching historical data", level="INFO")
        exchange = ccxt.binance()
        try:
            return await fetch_historical_hit_rates(exchange, symbol, timeframe)
        finally:
            await exchange.close()
            gc.collect()
    
    except Exception as e:
        log(f"[{symbol}] Error in get_tp_hit_rates: {e}", level="ERROR")
        return 0.0, 0.0, 0.0

async def fetch_historical_hit_rates(exchange, symbol: str, timeframe: str):
    try:
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=30)
        log(f"[{symbol}] Fetched {len(ohlcv)} klines from Binance")
        
        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
            dtype="float16"
        )
        
        df = calculate_indicators(df)
        if df is None:
            log(f"[{symbol}] Failed to calculate indicators for backtest", level="WARNING")
            return 0.0, 0.0, 0.0
            
        df["bullish_engulfing"] = is_bullish_engulfing(df).astype(float)
        df["bearish_engulfing"] = is_bearish_engulfing(df).astype(float)
        df["doji"] = is_doji(df).astype(float)
        df["hammer"] = is_hammer(df).astype(float)
        df["shooting_star"] = is_shooting_star(df).astype(float)
        df["three_white_soldiers"] = is_three_white_soldiers(df).astype(float)
        df["three_black_crows"] = is_three_black_crows(df).astype(float)
        
        tp1_hits = 0
        tp2_hits = 0
        tp3_hits = 0
        total_trades = 0
        
        for i in range(len(df) - 1):
            current_price = df["close"].iloc[i]
            future_high = df["high"].iloc[i + 1]
            future_low = df["low"].iloc[i + 1]
            atr = df["atr"].iloc[i]
            
            is_bullish = (
                df["bullish_engulfing"].iloc[i] or
                df["hammer"].iloc[i] or
                df["three_white_soldiers"].iloc[i] or
                (df["rsi"].iloc[i] < 40 and df["macd"].iloc[i] > df["macd_signal"].iloc[i])
            )
            is_bearish = (
                df["bearish_engulfing"].iloc[i] or
                df["shooting_star"].iloc[i] or
                df["three_black_crows"].iloc[i] or
                (df["rsi"].iloc[i] > 60 and df["macd"].iloc[i] < df["macd_signal"].iloc[i])
            )
            
            if is_bullish:
                tp1 = current_price + (0.15 * atr)
                tp2 = current_price + (0.3 * atr)
                tp3 = current_price + (0.45 * atr)
                
                if future_high >= tp1:
                    tp1_hits += 1
                if future_high >= tp2:
                    tp2_hits += 1
                if future_high >= tp3:
                    tp3_hits += 1
                total_trades += 1
            
            if is_bearish:
                tp1 = current_price - (0.15 * atr)
                tp2 = current_price - (0.3 * atr)
                tp3 = current_price - (0.45 * atr)
                
                if future_low <= tp1:
                    tp1_hits += 1
                if future_low <= tp2:
                    tp2_hits += 1
                if future_low <= tp3:
                    tp3_hits += 1
                total_trades += 1
        
        tp1_rate = min(tp1_hits / total_trades if total_trades > 0 else 0.0, 0.95)
        tp2_rate = min(tp2_hits / total_trades if total_trades > 0 else 0.0, 0.85)
        tp3_rate = min(tp3_hits / total_trades if total_trades > 0 else 0.0, 0.75)
        
        log(f"[{symbol}] Historical TP1 hit rate: {tp1_rate:.2%}, TP2: {tp2_rate:.2%}, TP3: {tp3_rate:.2%}")
        return tp1_rate, tp2_rate, tp3_rate
    
    except Exception as e:
        log(f"[{symbol}] Error fetching historical hit rates: {e}", level="ERROR")
        return 0.0, 0.0, 0.0
    finally:
        if 'df' in locals():
            del df
        gc.collect()
