import asyncio
import pandas as pd
from core.indicators import calculate_indicators
from utils.logger import log

TIMEFRAMES = ['15m', '1h', '4h', '1d']

async def fetch_ohlcv(exchange, symbol, timeframe, limit=100):
    try:
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not ohlcv or len(ohlcv) < 50:
            log(f"[{symbol}] Insufficient OHLCV data for {timeframe}", level='ERROR')
            return None
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'], dtype='float32')
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
            log(f"[{symbol}] Skipping {tf} due to fetch failure", level='ERROR')
            continue
        signal = calculate_indicators(symbol, df)
        if signal is None:
            log(f"[{symbol}] No signal for {tf}", level='ERROR')
            continue
        all_data[tf] = signal

    if not all_data:
        log(f"[{symbol}] No valid signals for any timeframe", level='ERROR')
        return {
            'symbol': symbol,
            'signal': None,
            'confidence': 0,
            'tp1_chance': 0,
            'atr': 0.01
        }

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
        log(f"[{symbol}] No valid decisions", level='ERROR')
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
    
    # 15m ٹائم فریم سے مکمل سگنل لے لو اگر فیصلہ میچ کرتا ہے
    primary_signal = all_data.get('15m', {})
    if primary_signal.get('direction') == final_dir:
        log(f"[{symbol}] Using 15m signal for full details")
        return {
            'symbol': symbol,
            'signal': final_dir,
            'confidence': avg_confidence,
            'tp1_chance': avg_tp1,
            'price': primary_signal.get('price', 0),
            'tp1': primary_signal.get('tp1', 0),
            'tp2': primary_signal.get('tp2', 0),
            'tp3': primary_signal.get('tp3', 0),
            'sl': primary_signal.get('sl', 0),
            'atr': primary_signal.get('atr', 0.01),
            'leverage': primary_signal.get('leverage', 10),
            'trade_type': primary_signal.get('trade_type', 'Scalping'),
            'tp2_possibility': primary_signal.get('tp2_possibility', 0),
            'tp3_possibility': primary_signal.get('tp3_possibility', 0),
            'support': primary_signal.get('support', 0),
            'resistance': primary_signal.get('resistance', 0)
        }
    
    log(f"[{symbol}] Fallback to basic signal")
    return {
        'symbol': symbol,
        'signal': final_dir,
        'confidence': avg_confidence,
        'tp1_chance': avg_tp1,
        'atr': primary_signal.get('atr', 0.01)
    }
