import logging
import os
from datetime import datetime
import pandas as pd

def log(message, level='INFO'):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    if level == 'INFO':
        print(log_entry)
    with open("logs/app.log", "a") as f:
        f.write(log_entry + "\n")

def log_signal_to_csv(signal):
    try:
        csv_path = "logs/signals_log.csv"
        timestamp = datetime.fromtimestamp(signal.get("timestamp", 0) / 1000).strftime('%Y-%m-%d %H:%M:%S')
        data = {
            "symbol": signal.get("symbol", ""),
            "price": signal.get("price", 0),
            "direction": signal.get("prediction", ""),
            "tp1": signal.get("tp1", 0),
            "tp2": signal.get("tp2", 0),
            "tp3": signal.get("tp3", 0),
            "sl": signal.get("sl", 0),
            "confidence": signal.get("confidence", 0),
            "trade_type": signal.get("trade_type", ""),
            "timestamp": timestamp,
            "tp1_possibility": signal.get("tp1_possibility", 0),
            "tp2_possibility": signal.get("tp2_possibility", 0),
            "tp3_possibility": signal.get("tp3_possibility", 0)
        }
        df = pd.DataFrame([data])

        if os.path.exists(csv_path):
            old_df = pd.read_csv(csv_path)
            if not df.empty and not df.isna().all().all():
                df = pd.concat([old_df, df], ignore_index=True)

        if not df.empty and not df.isna().all().all():
            df.to_csv(csv_path, index=False)
            log(f"📝 Signal logged to CSV for {signal.get('symbol', '')}")
        else:
            log("⚠️ No valid data to log to CSV")
    except Exception as e:
        log(f"❌ Error logging signal to CSV: {e}")
