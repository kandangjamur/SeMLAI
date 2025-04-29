import numpy as np
from core.indicators import calculate_indicators
from utils.logger import log

TIMEFRAMES = ["15m", "1h", "4h", "1d"]

def multi_timeframe_analysis(symbol, exchange):
    timeframe_results = []
    for tf in TIMEFRAMES:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
            if not ohlcv or len(ohlcv) < 50:
                continue

            signal = calculate_indicators(symbol, ohlcv)
            if signal and not np.isnan(signal.get('confidence', 0)) and not np.isnan(signal.get('price', 0)):
                timeframe_results.append(signal)
        except Exception:
            continue

    strong = [s for s in timeframe_results if s['confidence'] >= 75]
    if len(strong) >= 3:
        return strong[0]
    return None
