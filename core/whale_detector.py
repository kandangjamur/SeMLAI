import pandas as pd
from utils.logger import log

def detect_whale_activity(symbol, df):
    try:
        if len(df) < 20:
            log(f"[{symbol}] Insufficient data for whale detection", level='WARNING')
            return False

        volume_sma_5 = df["volume"].rolling(window=5).mean().iloc[-1]
        current_volume = df["volume"].iloc[-1]
        volume_threshold = 1_000_000  # Reduced from 2M USDT

        if current_volume > volume_threshold and current_volume > 1.5 * volume_sma_5:
            log(f"[{symbol}] Whale activity detected: Volume {current_volume:.2f} > {volume_threshold:.2f}")
            return True
        else:
            log(f"[{symbol}] Insufficient whale volume: {current_volume:.2f}", level='WARNING')
            return False
    except Exception as e:
        log(f"[{symbol}] Error in whale detection: {e}", level='ERROR')
        return False
