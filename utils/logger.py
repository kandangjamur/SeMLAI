import csv
import os
from datetime import datetime

def log(message):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def log_signal_to_csv(signal):
    log_path = "logs/signals_log.csv"
    headers = [
        'symbol', 'confidence', 'trade_type', 'prediction',
        'price', 'tp1', 'tp2', 'tp3', 'sl', 'timestamp'
    ]
    row = [
        signal['symbol'], signal['confidence'], signal['trade_type'], signal.get('prediction', ''),
        signal['price'], signal['tp1'], signal['tp2'], signal['tp3'], signal['sl'], signal['timestamp']
    ]
    file_exists = os.path.isfile(log_path)
    os.makedirs("logs", exist_ok=True)
    with open(log_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(headers)
        writer.writerow(row)
