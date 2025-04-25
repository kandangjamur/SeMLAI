def detect_sr_levels(df):
    support = df["low"].rolling(20).min().iloc[-1]
    resistance = df["high"].rolling(20).max().iloc[-1]
    return {"support": support, "resistance": resistance}
