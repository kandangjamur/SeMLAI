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

async def get_tp_hit_rates(symbol: str, timeframe: str):
    try:
        exchange = ccxt.binance()
        # Check if enough backtest data exists
        backtest_file = "logs/signals_log.csv"
        if not pd.io.common.file_exists(backtest_file):
            log(f"[{symbol}] No backtest data found, fetching historical data", level="INFO")
            return await fetch_historical_hit_rates(exchange, symbol, timeframe)

        df = pd.read_csv(backtest_file)
        df = df[df["symbol"] == symbol]
        
        if len(df) < 10:
            log(f"[{symbol}] Insufficient backtest data: {len(df)} trades, fetching historical data", level="INFO")
            return await fetch_historical_hit_rates(exchange, symbol, timeframe)
        
        # Calculate hit rates based on historical signals
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
    
    except Exception as e:
        log(f"[{symbol}] Error in get_tp_hit_rates: {e}", level="ERROR")
        return 0.0, 0.0, 0.0
    finally:
        await exchange.close()

async def fetch_historical_hit_rates(exchange, symbol: str, timeframe: str):
    try:
        # Fetch historical klines
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=200)  # Reduced to 200
        log(f"[{symbol}] Fetched {len(ohlcv)} klines from Binance")
        
        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
            dtype="float32"
        )
        
        # Calculate indicators and candlestick patterns
        df = calculate_indicators(df)
        df["bullish_engulfing"] = is_bullish_engulfing(df).astype(float)
        df["bearish_engulfing"] = is_bearish_engulfing(df).astype(float)
        df["doji"] = is_doji(df).astype(float)
        df["hammer"] = is_hammer(df).astype(float)
        df["shooting_star"] = is_shooting_star(df).astype(float)
        df["three_white_soldiers"] = is_three_white_soldiers(df).astype(float)
        df["three_black_crows"] = is_three_black_crows(df).astype(float)
        
        # Simulate trades based on technical analysis
        tp1_hits = 0
        tp2_hits = 0
        tp3_hits = 0
        total_trades = 0
        
        for i in range(len(df) - 1):
            current_price = df["close"].iloc[i]
            future_high = df["high"].iloc[i + 1]
            future_low = df["low"].iloc[i + 1]
            atr = df["atr"].iloc[i]
            
            # Determine trade direction based on technical signals
            is_bullish = (
                df["bullish_engulfing"].iloc[i] or
                df["hammer"].iloc[i] or
                df["three_white_soldiers"].iloc[i] or
                (df["rsi"].iloc[i] < 30 and df["macd"].iloc[i] > df["macd_signal"].iloc[i])
            )
            is_bearish = (
                df["bearish_engulfing"].iloc[i] or
                df["shooting_star"].iloc[i] or
                df["three_black_crows"].iloc[i] or
                (df["rsi"].iloc[i] > 70 and df["macd"].iloc[i] < df["macd_signal"].iloc[i])
            )
            
            if is_bullish:
                # LONG trade
                tp1 = current_price + (0.3 * atr)  # Adjusted for higher hit rate
                tp2 = current_price + (0.6 * atr)
                tp3 = current_price + (0.9 * atr)
                
                if future_high >= tp1:
                    tp1_hits += 1
                if future_high >= tp2:
                    tp2_hits += 1
                if future_high >= tp3:
                    tp3_hits += 1
                total_trades += 1
            
            if is_bearish:
                # SHORT trade
                tp1 = current_price - (0.3 * atr)  # Adjusted for higher hit rate
                tp2 = current_price - (0.6 * atr)
                tp3 = current_price - (0.9 * atr)
                
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
        await exchange.close()
