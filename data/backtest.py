import pandas as pd
import numpy as np
from utils.logger import log
from binance.client import AsyncClient

async def get_tp_hit_rates(symbol: str, timeframe: str = None, backtest_file: str = "logs/signals_log.csv"):
    """
    Calculate TP1, TP2, TP3 hit rates from backtest file or historical data.

    Args:
        symbol (str): Symbol (e.g., BTC/USDT)
        timeframe (str, optional): Timeframe (e.g., 15m, 1h, 4h)
        backtest_file (str): Path to backtest file (default: logs/signals_log.csv)

    Returns:
        tuple: (tp1_hit_rate, tp2_hit_rate, tp3_hit_rate) as floats between 0 and 1
    """
    try:
        # Try reading from signals_log.csv
        df = pd.read_csv(backtest_file)
        filtered_df = df[df["symbol"] == symbol]
        
        if timeframe and "timeframe" in df.columns:
            filtered_df = filtered_df[filtered_df["timeframe"] == timeframe]
        
        if len(filtered_df) >= 10:
            tp1_rate = (filtered_df["status"] == "tp1").mean()
            tp2_rate = (filtered_df["status"] == "tp2").mean()
            tp3_rate = (filtered_df["status"] == "tp3").mean()
            if pd.isna(tp1_rate) or pd.isna(tp2_rate) or pd.isna(tp3_rate):
                log(f"[{symbol}] Invalid TP hit rates, fetching historical data", level="WARNING")
            else:
                log(f"[{symbol}] TP1 hit rate: {tp1_rate:.2%}, TP2: {tp2_rate:.2%}, TP3: {tp3_rate:.2%}")
                return tp1_rate or 0.7, tp2_rate or 0.5, tp3_rate or 0.3
        
        # If insufficient data, fetch historical data from Binance
        log(f"[{symbol}] Insufficient backtest data: {len(filtered_df)} trades, fetching historical data")
        client = await AsyncClient.create()
        klines = await client.get_historical_klines(
            symbol, timeframe, "2000 hours ago UTC"
        )
        await client.close_connection()
        
        if not klines or len(klines) < 200:
            log(f"[{symbol}] Insufficient historical data: {len(klines)} trades", level="WARNING")
            return 0.7, 0.5, 0.3
        
        backtest_df = pd.DataFrame(
            klines,
            columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base', 'taker_buy_quote', 'ignore'
            ]
        )
        backtest_df['close'] = backtest_df['close'].astype(float)
        
        hit_tp1, hit_tp2, hit_tp3 = 0, 0, 0
        total_trades = 0
        
        for i in range(len(backtest_df) - 100, len(backtest_df)):
            current_price = backtest_df['close'].iloc[i]
            future_prices = backtest_df['close'].iloc[i:i+50]
            
            # Calculate TP levels based on volatility
            volatility = backtest_df['close'].pct_change().std() * np.sqrt(252)
            tp1 = current_price * (1 + 0.5 * volatility) if 'LONG' else current_price * (1 - 0.5 * volatility)
            tp2 = current_price * (1 + 1.0 * volatility) if 'LONG' else current_price * (1 - 1.0 * volatility)
            tp3 = current_price * (1 + 1.5 * volatility) if 'LONG' else current_price * (1 - 1.5 * volatility)
            
            if not all([tp1, tp2, tp3]) or any(np.isclose([tp1, tp2, tp3], current_price, rtol=1e-5)):
                continue
            
            total_trades += 1
            if 'LONG':
                if any(future_prices >= tp1):
                    hit_tp1 += 1
                if any(future_prices >= tp2):
                    hit_tp2 += 1
                if any(future_prices >= tp3):
                    hit_tp3 += 1
            else:  # SHORT
                if any(future_prices <= tp1):
                    hit_tp1 += 1
                if any(future_prices <= tp2):
                    hit_tp2 += 1
                if any(future_prices <= tp3):
                    hit_tp3 += 1
        
        if total_trades == 0:
            log(f"[{symbol}] No valid trades in backtest", level="WARNING")
            return 0.7, 0.5, 0.3
        
        tp1_rate = hit_tp1 / total_trades
        tp2_rate = hit_tp2 / total_trades
        tp3_rate = hit_tp3 / total_trades
        
        log(f"[{symbol}] Historical TP1 hit rate: {tp1_rate:.2%}, TP2: {tp2_rate:.2%}, TP3: {tp3_rate:.2%}")
        return tp1_rate, tp2_rate, tp3_rate
    
    except FileNotFoundError:
        log(f"Backtest file {backtest_file} not found, using historical data", level="WARNING")
        # Fetch historical data as fallback
        return await get_tp_hit_rates(symbol, timeframe)  # Recursive call without file
    except Exception as e:
        log(f"Error calculating TP hit rates for {symbol}: {str(e)}", level="ERROR")
        return 0.7, 0.5, 0.3
