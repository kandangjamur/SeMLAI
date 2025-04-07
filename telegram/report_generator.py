from core.analysis import generate_signals

def generate_report():
    signals = generate_signals()
    report = "End of Day Report\n\n"
    for signal in signals:
        report += f"Symbol: {signal['symbol']} - RSI: {signal['rsi']} - MACD: {signal['macd']}\n"
    return report
