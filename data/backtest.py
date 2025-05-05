import pandas as pd
from core.indicators import calculate_indicators
import ccxt.async_support as ccxt
from utils.logger import log
import asyncio

async def run_backtest_symbol(exchange, symbol):
    try:
        results = []
        timeframes = ['15m', '1h', '4h']
        for tf in timeframes:
            limit = 2880 if tf == '15m' else 720 if tf == '1h' else 180  # ~30 days
            ohlcv = await exchange.fetch_ohlcv(symbol, tf, limit=limit)
            if len(ohlcv) < 50:
                continue

            for i in range(50, len(ohlcv)-10):
                subset = ohlcv[i-50:i]
                signal = calculate_indicators(symbol, subset)
                if not signal or signal['confidence'] < 80:
                    continue

                highs = [c[2] for c in ohlcv[i+1:i+10]]
                lows = [c[3] for c in ohlcv[i+1:i+10]]
                status = "pending"
                
                if signal["direction"] == "LONG":
                    if signal["tp3"] <= max(highs):
                        status = "tp3"
                    elif signal["tp2"] <= max(highs):
                        status = "tp2"
                    elif signal["tp1"] <= max(highs):
                        status = "tp1"
                    elif signal["sl"] >= min(lows):
                        status = "sl"
                else:  # SHORT
                    if signal["tp3"] >= min(lows):
                        status = "tp3"
                    elif signal["tp2"] >= min(lows):
                        status = "tp2"
                    elif signal["tp1"] >= min(lows):
                        status = "tp1"
                    elif signal["sl"] <= max(highs):
                        status = "sl"

                results.append({
                    "symbol": symbol,
                    "confidence": signal["confidence"],
                    "trade_type": signal["trade_type"],
                    "tp1": signal["tp1"],
                    "tp2": signal["tp2"],
                    "tp3": signal["tp3"],
                    "sl": signal["sl"],
                    "status": status,
                    "timeframe": tf
                })

        if not results:
            log(f"[{symbol}] No backtest results", level='WARNING')
            return None

        df = pd.DataFrame(results)
        tp1_hits = len(df[df['status'] == 'tp1'])
        total = len(df)
        tp1_hit_rate = round((tp1_hits / total * 100) if total > 0 else 0, 2)

        # Multi-timeframe confirmation
        tf_counts = df['timeframe'].value_counts()
        if len(tf_counts) < 2:
            log(f"[{symbol}] Insufficient multi-timeframe data", level='WARNING')
            return None

        log(f"[{symbol}] Backtest complete: TP1 hit rate = {tp1_hit_rate}%")
        return {"tp1_hit_rate": tp1_hit_rate}

    except Exception as e:
        log(f"[{symbol}] Backtest Error: {e}", level='ERROR')
        return None
