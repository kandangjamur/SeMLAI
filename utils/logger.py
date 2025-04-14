import csv
import os
from datetime import datetime

def log(message):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def log_signal_to_csv(signal):
    log_path = "logs/signals_log.csv"
    os.makedirs("logs", exist_ok=True)
    file_exists = os.path.isfile(log_path)
    
    with open(log_path, "a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["datetime", "symbol", "type", "direction", "confidence", "tp1", "tp2", "tp3", "sl", "status"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            signal['symbol'],
            signal['trade_type'],
            signal['direction'],
            signal['confidence'],
            signal['tp1'],
            signal['tp2'],
            signal['tp3'],
            signal['sl'],
            "OPEN"
        ])
