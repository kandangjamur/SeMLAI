import logging
import os
import pandas as pd
from datetime import datetime

def log(msg):
    logging.info(msg)

def log_signal_to_csv(signal):
    filename = "logs/signals_log.csv"
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    df = pd.DataFrame([{
        "timestamp": signal['timestamp'],
        "symbol": signal['symbol'],
        "price": signal['price'],
        "confidence": signal['confidence'],
        "tp1": signal['tp1'],
        "tp2": signal['tp2'],
        "tp3": signal['tp3'],
        "sl": signal['sl'],
        "type": signal['trade_type'],
        "direction": signal['prediction'],
        "leverage": signal['leverage'],
        "tp1_possibility": signal.get("tp1_possibility", 0),
        "tp2_possibility": signal.get("tp2_possibility", 0),
        "tp3_possibility": signal.get("tp3_possibility", 0),
        "status": "pending"
    }])

    if os.path.exists(filename):
        old_df = pd.read_csv(filename)
        df = pd.concat([old_df, df], ignore_index=True)

    df.to_csv(filename, index=False)
    log(f"📝 Signal logged to CSV for {signal['symbol']}")

# لاگنگ سیٹ اپ
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)
