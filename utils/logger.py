import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import pandas as pd

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

log_formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

log_file = os.path.join(LOG_DIR, "bot.log")
file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

logger = logging.getLogger("crypto-signal-bot")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)
logger.propagate = False

def log(message, level='INFO'):
    if level == 'INFO':
        logger.info(message)
    elif level == 'ERROR':
        logger.error(message)

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
            log(f"Signal logged to CSV for {signal.get('symbol', '')}")
        else:
            log("No valid data to log to CSV", level='ERROR')
    except Exception as e:
        log(f"Error logging signal to CSV: {e}", level='ERROR')
