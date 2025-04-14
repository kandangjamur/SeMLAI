import pandas as pd
import ta

def calculate_indicators(symbol, ohlcv):
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
    df['ema'] = ta.trend.EMAIndicator(df['close']).ema_indicator()
    df['macd'] = ta.trend.MACD(df['close']).macd()
    df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    score = 0
    if last['rsi'] < 30:
        score += 30
    if last['close'] > last['ema']:
        score += 30
    if last['macd'] > 0:
        score += 30
    if last['close'] > prev['close']:
        score += 10

    confidence = min(score, 100)
    direction = "LONG" if last['macd'] > 0 and last['close'] > last['ema'] else "SHORT"

    entry = last['close']
    atr = last['atr']
    tp1 = round(entry + (atr * 1.5), 4)
    tp2 = round(entry + (atr * 2), 4)
    tp3 = round(entry + (atr * 2.5), 4)
    sl = round(entry - (atr * 1.2), 4)
    leverage = 5 if confidence < 80 else 10 if confidence < 90 else 15

    return {
        'symbol': symbol,
        'price': entry,
        'rsi': last['rsi'],
        'macd': last['macd'],
        'confidence': confidence,
        'direction': direction,
        'type': 'BUY' if direction == 'LONG' else 'SELL',
        'leverage': leverage,
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3,
        'sl': sl
    }
