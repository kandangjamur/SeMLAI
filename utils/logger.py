import os
import csv
from datetime import datetime

def log(message):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def log_signal_to_csv(signal):
    path = "logs/signals_log.csv"
    os.makedirs("logs", exist_ok=True)

    if not os.path.exists(path):
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=signal.keys())
            writer.writeheader()

    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=signal.keys())
        writer.writerow(signal)
