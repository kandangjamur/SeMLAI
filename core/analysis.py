import numpy as np
from core.indicators import calculate_indicators
from utils.logger import log

TIMEFRAMES = ["15m", "1h", "4h", "1d"]

async def multi_timeframe_analysis(symbol, exchange):
    try:
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

        strong = [s for s in timeframe_results if s['confidence'] >= 50]

        if len(strong) >= 3 or (len(strong) >= 2 and any(s['confidence'] > 60 for s in strong)):
            prices = [s["price"] for s in strong]
            types = set([s["trade_type"] for s in strong])
            directions = set([s["direction"] for s in strong])
            avg_conf = np.mean([s["confidence"] for s in strong])

            if max(prices) - min(prices) > min(prices) * 0.025:
                log(f"⚠️ Price deviation too high for {symbol} across timeframes")
                return None

            if len(types) > 1:
                log(f"⚠️ Inconsistent trade types for {symbol}: {types}")
                return None

            if len(directions) > 1:
                log(f"⚠️ Inconsistent directions for {symbol}: {directions}")
                return None

            best_signal = max(strong, key=lambda s: s["confidence"])
            best_signal["confidence"] = round(min(avg_conf, 100), 2)
            log(f"✅ Strong multi-timeframe signal for {symbol}: direction={best_signal['direction']}, avg confidence={avg_conf}")
            return best_signal

        log(f"⚠️ No consistent strong signals for {symbol}")
        return None
    except Exception as e:
        log(f"❌ Error in multi_timeframe_analysis for {symbol}: {e}")
        return None
