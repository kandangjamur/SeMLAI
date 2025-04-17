def classify_trade(signal):
    confidence = signal['confidence']
    if confidence >= 90:
        return "Spot"
    elif confidence >= 75:
        return "Normal"
    else:
        return "Scalping"
