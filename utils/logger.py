# utils/logger.py
import os
from datetime import datetime
import pandas as pd

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with open("logs/app.log", "a") as f:
        f.write(log_entry + "\n")

def log_signal_to_csv(signal):
    try:
        path = "logs/signals_log.csv"
        ts = datetime.fromtimestamp(signal.get("timestamp", 0) / 1000).strftime('%Y-%m-%d %H:%M:%S')
        row = {
            "symbol": signal["symbol"],
            "price": signal["price"],
            "direction": signal["prediction"],
            "tp1": signal["tp1"],
            "tp2": signal["tp2"],
            "tp3": signal["tp3"],
            "sl": signal["sl"],
            "confidence": signal["confidence"],
            "trade_type": signal["trade_type"],
            "timestamp": ts,
            "tp1_possibility": signal.get("tp1_possibility", 0),
            "tp2_possibility": signal.get("tp2_possibility", 0),
            "tp3_possibility": signal.get("tp3_possibility", 0)
        }
        df = pd.DataFrame([row])
        if os.path.exists(path):
            df = pd.concat([pd.read_csv(path), df], ignore_index=True)
        df.to_csv(path, index=False)
    except Exception as e:
        log(f"Error logging signal to CSV: {e}", level="ERROR")
