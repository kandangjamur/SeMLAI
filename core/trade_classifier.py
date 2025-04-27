# core/trade_classifier.py

def classify_trade(confidence):
    if confidence >= 80:
        return "Normal"
    elif 70 <= confidence < 80:
        return "Scalping"
    else:
        return None  # Ignore low-confidence signals
