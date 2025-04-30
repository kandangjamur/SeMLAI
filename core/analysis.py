import numpy as np
from core.indicators import calculate_indicators
from utils.logger import log

TIMEFRAMES = ["15m", "1h", "4h", "1d"]

async def multi_timeframe_analysis(symbol, exchange):
    timeframe_results = []

    for tf in TIMEFRAMES:
        try:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
            if not ohlcv or len(ohlcv) < 50:
                log(f"⚠️ Insufficient data for {symbol} on {tf}: {len(ohlcv)} candles")
                continue

            signal = calculate_indicators(symbol, ohlcv)
            if signal and not np.isnan(signal.get('confidence', 0)) and not np.isnan(signal.get('price', 0)):
                signal["timeframe"] = tf
                timeframe_results.append(signal)
            else:
                log(f"⚠️ Invalid signal for {symbol} on {tf}")
        except Exception as e:
            log(f"❌ Error in {symbol} on {tf}: {e}")
            continue

    strong = [s for s in timeframe_results if s['confidence'] >= 60]

    if len(strong) >= 3:
        prices = [s["price"] for s in strong]
        types = set([s["trade_type"] for s in strong])
        avg_conf = np.mean([s["confidence"] for s in strong])

        if max(prices) - min(prices) > min(prices) * 0.02:
            log(f"⚠️ Price deviation too high for {symbol} across timeframes")
            return None

        if len(types) > 1:
            log(f"⚠️ Inconsistent trade types for {symbol}: {types}")
            return None

        best_signal = max(strong, key=lambda s: s["confidence"])
        best_signal["confidence"] = round(avg_conf, 2)
        log(f"✅ Strong multi-timeframe signal for {symbol} with avg confidence {avg_conf}")
        return best_signal

    log(f"⚠️ No consistent strong signals for {symbol}")
    return None
