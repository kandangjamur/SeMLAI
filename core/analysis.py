# core/analysis.py
import numpy as np
from core.indicators import calculate_indicators
from utils.logger import log

TIMEFRAMES = ["15m", "1h", "4h", "1d"]

async def multi_timeframe_analysis(symbol, exchange):
    try:
        results = []
        for tf in TIMEFRAMES:
            try:
                ohlcv = await exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
                if not ohlcv or len(ohlcv) < 50:
                    continue
                signal = calculate_indicators(symbol, ohlcv)
                if signal and not np.isnan(signal.get("confidence", 0)):
                    signal["timeframe"] = tf
                    results.append(signal)
            except Exception as e:
                log(f"Error on {symbol} {tf}: {e}")
                continue

        strong = [r for r in results if r["confidence"] >= 50]
        if len(strong) >= 3 or (len(strong) >= 2 and any(s["confidence"] > 60 for s in strong)):
            prices = [s["price"] for s in strong]
            if max(prices) - min(prices) > min(prices) * 0.025:
                return None

            types = set(s["trade_type"] for s in strong)
            directions = set(s["direction"] for s in strong)
            if len(types) > 1 or len(directions) > 1:
                return None

            best = max(strong, key=lambda s: s["confidence"])
            best["confidence"] = round(np.mean([s["confidence"] for s in strong]), 2)
            log(f"✅ Strong multi-timeframe signal for {symbol}: {best['direction']}, {best['confidence']}")
            return best

        return None
    except Exception as e:
        log(f"multi_timeframe_analysis error for {symbol}: {e}")
        return None
