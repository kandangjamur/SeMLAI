def classify_trade_type(confidence):
    if confidence >= 90:
        return "Normal"
    elif confidence >= 85:
        return "Scalping"
    return None
