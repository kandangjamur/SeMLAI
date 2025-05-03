import numpy as np
import pandas as pd
import ta

def calculate_indicators(ohlcv, timeframe):
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    if df.isnull().values.any() or len(df) < 50:
        return None

    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    df['ema_20'] = ta.trend.EMAIndicator(df['close'], window=20).ema_indicator()
    df['ema_50'] = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator()
    df['macd'] = ta.trend.MACD(df['close']).macd_diff()

    df['bullish_engulfing'] = (df['close'].shift(1) < df['open'].shift(1)) & \
                              (df['close'] > df['open']) & \
                              (df['open'] < df['close'].shift(1)) & \
                              (df['close'] > df['open'].shift(1))

    df['bearish_engulfing'] = (df['close'].shift(1) > df['open'].shift(1)) & \
                              (df['close'] < df['open']) & \
                              (df['open'] > df['close'].shift(1)) & \
                              (df['close'] < df['open'].shift(1))

    latest = df.iloc[-1]
    signal = None
    confidence = 0
    tp_levels = {}

    if latest['rsi'] < 30 and latest['close'] > latest['ema_20'] and latest['macd'] > 0 and latest['bullish_engulfing']:
        signal = "LONG"
        confidence += 60
    elif latest['rsi'] > 70 and latest['close'] < latest['ema_20'] and latest['macd'] < 0 and latest['bearish_engulfing']:
        signal = "SHORT"
        confidence += 60

    if latest['close'] > latest['ema_50']:
        confidence += 20 if signal == "LONG" else 0
    elif latest['close'] < latest['ema_50']:
        confidence += 20 if signal == "SHORT" else 0

    if signal:
        tp1 = round(latest['close'] * (1.01 if signal == "LONG" else 0.99), 4)
        tp2 = round(latest['close'] * (1.02 if signal == "LONG" else 0.98), 4)
        tp_levels = {"tp1": tp1, "tp2": tp2}

    return {
        "signal": signal,
        "confidence": confidence,
        "tp_levels": tp_levels
    }
