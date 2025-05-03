import pandas as pd
from core.indicators import calculate_indicators

def analyze_symbol(df_15m, df_1h, df_4h, df_1d):
    df_15m = calculate_indicators(df_15m)
    df_1h = calculate_indicators(df_1h)
    df_4h = calculate_indicators(df_4h)
    df_1d = calculate_indicators(df_1d)

    if (
        df_15m is None or df_1h is None or
        df_4h is None or df_1d is None or
        df_15m.empty or df_1h.empty or
        df_4h.empty or df_1d.empty
    ):
        return None

    signal = {"signal": "none", "confidence": 0}

    for df in [df_15m, df_1h, df_4h, df_1d]:
        if df is None or df.empty or 'close' not in df.columns:
            return None

    conditions = []

    if (
        df_15m['RSI'].iloc[-1] > 50 and
        df_1h['RSI'].iloc[-1] > 50 and
        df_4h['RSI'].iloc[-1] > 50 and
        df_1d['RSI'].iloc[-1] > 50
    ):
        signal['signal'] = "long"
        conditions.append("RSI>50")

    elif (
        df_15m['RSI'].iloc[-1] < 50 and
        df_1h['RSI'].iloc[-1] < 50 and
        df_4h['RSI'].iloc[-1] < 50 and
        df_1d['RSI'].iloc[-1] < 50
    ):
        signal['signal'] = "short"
        conditions.append("RSI<50")

    signal['confidence'] = len(conditions) * 25
    return signal if signal['signal'] != "none" else None
