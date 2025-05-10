import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from utils.logger import log
import asyncio

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
        
        # Calculate hit rates
        tp1_hits = len(df[df["tp1"] <= df["price"]]) if "LONG" in df["prediction"].values else len(df[df["tp1"] >= df["price"]])
        tp2_hits = len(df[df["tp2"] <= df["price"]]) if "LONG" in df["prediction"].values else len(df[df["tp2"] >= df["price"]])
        tp3_hits = len(df[df["tp3"] <= df["price"]]) if "LONG" in df["prediction"].values else len(df[df["tp3"] >= df["price"]])
        
        total_trades = len(df)
        tp1_rate = tp1_hits / total_trades if total_trades > 0 else 0.0
        tp2_rate = tp2_hits / total_trades if total_trades > 0 else 0.0
        tp3_rate = tp3_hits / total_trades if total_trades > 0 else 0.0
        
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
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=500)  # Reduced to 500
        log(f"[{symbol}] Fetched {len(ohlcv)} klines from Binance")
        
        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
            dtype="float32"
        )
        
        # Simulate trades
        tp1_hits = 0
        tp2_hits = 0
        tp3_hits = 0
        total_trades = 0
        
        for i in range(len(df) - 1):
            current_price = df["close"].iloc[i]
            future_high = df["high"].iloc[i + 1]
            future_low = df["low"].iloc[i + 1]
            
            # Assume LONG trade
            tp1 = current_price * 1.02
            tp2 = current_price * 1.04
            tp3 = current_price * 1.06
            
            if future_high >= tp1:
                tp1_hits += 1
            if future_high >= tp2:
                tp2_hits += 1
            if future_high >= tp3:
                tp3_hits += 1
                
            total_trades += 1
        
        tp1_rate = tp1_hits / total_trades if total_trades > 0 else 0.0
        tp2_rate = tp2_hits / total_trades if total_trades > 0 else 0.0
        tp3_rate = tp3_hits / total_trades if total_trades > 0 else 0.0
        
        log(f"[{symbol}] Historical TP1 hit rate: {tp1_rate:.2%}, TP2: {tp2_rate:.2%}, TP3: {tp3_rate:.2%}")
        return tp1_rate, tp2_rate, tp3_rate
    
    except Exception as e:
        log(f"[{symbol}] Error fetching historical hit rates: {e}", level="ERROR")
        return 0.0, 0.0, 0.0
    finally:
        await exchange.close()
