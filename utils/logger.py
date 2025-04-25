import os
import csv
from datetime import datetime

LOG_FILE = "logs/signals_log.csv"
os.makedirs("logs", exist_ok=True)

def log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}")

def log_signal_to_csv(signal):
    headers = [
        "timestamp", "symbol", "price", "confidence", "trade_type",
        "prediction", "tp1", "tp2", "tp3", "tp1_prob", "tp2_prob", "tp3_prob",
        "sl", "leverage", "status"
    ]
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "timestamp": signal["timestamp"],
            "symbol": signal["symbol"],
            "price": signal["price"],
            "confidence": signal["confidence"],
            "trade_type": signal["trade_type"],
            "prediction": signal["prediction"],
            "tp1": signal["tp1"],
            "tp2": signal["tp2"],
            "tp3": signal["tp3"],
            "tp1_prob": signal.get("tp1_prob", ""),
            "tp2_prob": signal.get("tp2_prob", ""),
            "tp3_prob": signal.get("tp3_prob", ""),
            "sl": signal["sl"],
            "leverage": signal["leverage"],
            "status": "active"
        })
