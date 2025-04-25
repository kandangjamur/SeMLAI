import os
import pandas as pd
from datetime import datetime

log_path = "logs"
log_file = os.path.join(log_path, "signals_log.csv")

if not os.path.exists(log_path):
    os.makedirs(log_path)

def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def log_signal_to_csv(signal):
    row = {
        "timestamp": signal["timestamp"],
        "symbol": signal["symbol"],
        "confidence": signal["confidence"],
        "trade_type": signal["trade_type"],
        "direction": signal["prediction"],
        "price": signal["price"],
        "tp1": signal["tp1"],
        "tp2": signal["tp2"],
        "tp3": signal["tp3"],
        "sl": signal["sl"],
        "leverage": signal["leverage"],
        "status": "pending"
    }
    try:
        df = pd.DataFrame([row])
        if os.path.exists(log_file):
            df.to_csv(log_file, mode='a', header=False, index=False)
        else:
            df.to_csv(log_file, index=False)
        log(f"📥 Signal logged to CSV: {signal['symbol']}")
    except Exception as e:
        log(f"❌ CSV Logging Error: {e}")
