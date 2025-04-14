def classify_trade(signal):
    rsi = signal.get('rsi', 50)
    if rsi < 30:
        return "Scalping"
    elif 30 <= rsi < 50:
        return "Normal"
    else:
        return "Spot"
