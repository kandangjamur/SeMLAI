# utils/support_resistance.py
def detect_sr_levels(df):
    recent = df.tail(20)
    support = recent['low'].min()
    resistance = recent['high'].max()
    return {"support": support, "resistance": resistance}
