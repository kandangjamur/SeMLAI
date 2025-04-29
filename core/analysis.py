# core/analysis.py
import numpy as np
from core.indicators import calculate_indicators
from utils.logger import log

TIMEFRAMES = ["15m", "1h", "4h", "1d"]

def multi_timeframe_analysis(symbol, exchange):
    timeframe_results = []
    try:
        for tf in TIMEFRAMES:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
                if not ohlcv or len(ohlcv) < 50:
                    log(f"⚠️ Skipping {symbol} {tf} - insufficient candles")
                    continue

                signal = calculate_indicators(symbol, ohlcv)
                if signal and not np.isnan(signal.get('confidence', 0)) and not np.isnan(signal.get('price', 0)):
                    timeframe_results.append(signal)

            except Exception as e:
                log(f"❌ Error fetching {symbol} {tf}: {e}")

        strong_signals = [s for s in timeframe_results if s['confidence'] >= 75]

        if len(strong_signals) >= 3:
            return strong_signals[0]
        else:
            log(f"⏭️ Skipping {symbol} - not enough confirmations ({len(strong_signals)}/4)")
            return None

    except Exception as e:
        log(f"❌ Multi-timeframe analysis error {symbol}: {e}")
        return None
