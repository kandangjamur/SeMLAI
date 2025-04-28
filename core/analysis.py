import numpy as np
from core.indicators import calculate_indicators
from utils.logger import log

TIMEFRAMES = ["15m", "1h", "4h", "1d"]

def multi_timeframe_analysis(symbol, exchange):
    signals = []
    try:
        for tf in TIMEFRAMES:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
            if not ohlcv or len(ohlcv) < 50:
                continue
            signal = calculate_indicators(symbol, ohlcv)
            if signal and not np.isnan(signal.get('confidence', 0)):
                signals.append(signal)

        strong = [s for s in signals if s['confidence'] >= 75]
        if len(strong) >= 3:
            return strong[0]
        else:
            return None
    except Exception as e:
        log(f"❌ Analysis error {symbol}: {e}")
        return None
