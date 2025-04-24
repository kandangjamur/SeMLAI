import os
import pandas as pd
from datetime import datetime

def log(msg):
    now = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{now} {msg}")

def log_signal_to_csv(signal):
    os.makedirs("logs", exist_ok=True)
    path = "logs/signals_log.csv"
    row = {
        "symbol": signal["symbol"],
        "price": signal["price"],
        "tp1": signal["tp1"],
        "tp2": signal["tp2"],
        "tp3": signal["tp3"],
        "sl": signal["sl"],
        "confidence": signal["confidence"],
        "leverage": signal["leverage"],
        "type": signal["trade_type"],
        "prediction": signal["prediction"],
        "timestamp": int(datetime.utcnow().timestamp() * 1000),
        "status": "pending"
    }

    df = pd.DataFrame([row])
    if not os.path.exists(path):
        df.to_csv(path, index=False)
    else:
        df.to_csv(path, mode='a', header=False, index=False)
