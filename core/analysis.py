import asyncio
import pandas as pd
from core.indicators import calculate_indicators
from utils.logger import log

TIMEFRAMES = ['15m', '1h', '4h', '1d']

async def fetch_ohlcv(exchange, symbol, timeframe, limit=100):
    try:
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv or len(ohlcv) < 50:
            return None
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        log(f"[{symbol}] Failed to fetch OHLCV for {timeframe}: {e}", level='ERROR')
        return None

async def analyze_symbol(exchange, symbol):
    all_data = {}
    for tf in TIMEFRAMES:
        df = await fetch_ohlcv(exchange, symbol, tf)
        if df is None:
            return None
        signal = calculate_indicators(symbol, df)
        if signal is None:
            return None
        all_data[tf] = signal

    decisions = []
    confidences = []
    tp1_probs = []

    for tf, signal in all_data.items():
        direction = signal.get('direction', 'none')
        confidence = signal.get('confidence', 0)
        tp1_prob = signal.get('tp1_possibility', 0)

        if direction != 'none':
            decisions.append(direction)
            confidences.append(confidence)
            tp1_probs.append(tp1_prob)

    if not decisions:
        return {
            'symbol': symbol,
            'signal': None,
            'confidence': 0,
            'tp1_chance': 0,
            'atr': 0.01
        }

    final_dir = max(set(decisions), key=decisions.count)
    avg_confidence = round(sum(confidences) / len(confidences), 2)
    avg_tp1 = round(sum(tp1_probs) / len(tp1_probs), 2)
    atr = all_data['15m'].get('atr', 0.01)

    return {
        'symbol': symbol,
        'signal': final_dir,
        'confidence': avg_confidence,
        'tp1_chance': avg_tp1,
        'atr': atr
    }
