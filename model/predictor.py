import pandas as pd

def predict_trend(symbol, ohlcv):
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    last = df.iloc[-1]
    prev = df.iloc[-2]

    bullish = last['close'] > last['open']
    higher_high = last['high'] > prev['high']
    higher_low = last['low'] > prev['low']

    if bullish and higher_high and higher_low:
        return "LONG"
    elif not bullish and last['low'] < prev['low']:
        return "SHORT"
    return "SIDEWAYS"
