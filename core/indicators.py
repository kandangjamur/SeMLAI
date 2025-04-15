import pandas as pd
import ta

def calculate_indicators(symbol, ohlcv):
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])

    # Indicators
    df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
    df['ema'] = ta.trend.EMAIndicator(df['close']).ema_indicator()
    df['macd'] = ta.trend.MACD(df['close']).macd()
    df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()

    bb = ta.volatility.BollingerBands(df['close'])
    df['bb_low'] = bb.bollinger_lband()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    score = 0

    # RSI logic
    if last['rsi'] < 30:
        score += 35
    elif last['rsi'] < 50:
        score += 20

    # EMA
    if last['close'] > last['ema']:
        score += 20

    # MACD
    if last['macd'] > 0:
        score += 20

    # Candle strength
    if last['close'] > prev['close']:
        score += 10

    # Volume spike + BB breakout
    avg_vol = df['volume'].rolling(10).mean().iloc[-1]
    if last['volume'] > 2 * avg_vol and last['close'] < last['bb_low']:
        score += 10

    confidence = min(score, 100)

    # Direction logic
    if last['macd'] > 0 and last['close'] > last['ema']:
        direction = "LONG"
    elif last['macd'] < 0 and last['close'] < last['ema']:
        direction = "SHORT"
    else:
        direction = "SIDEWAYS"

    entry = last['close']
    atr = last['atr']
    tp1 = round(entry + atr * 1.2, 4) if direction == "LONG" else round(entry - atr * 1.2, 4)
    tp2 = round(entry + atr * 1.8, 4) if direction == "LONG" else round(entry - atr * 1.8, 4)
    tp3 = round(entry + atr * 2.4, 4) if direction == "LONG" else round(entry - atr * 2.4, 4)
    sl = round(entry - atr * 1.0, 4) if direction == "LONG" else round(entry + atr * 1.0, 4)

    leverage = 5 if confidence < 90 else 10 if confidence < 95 else 15

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
