import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import polars as pl
import shutil

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
    elif level == 'WARNING':
        logger.warning(message)

def log_signal_to_csv(signal):
    try:
        csv_path = "logs/signals_log.csv"
        timestamp = datetime.fromtimestamp(signal.get("timestamp", 0) / 1000).strftime('%Y-%m-%d %H:%M:%S')
        data = pl.DataFrame({
            "symbol": [signal.get("symbol", "")],
            "price": [signal.get("price", 0)],
            "direction": [signal.get("direction", "")],
            "tp1": [signal.get("tp1", 0)],
            "tp2": [signal.get("tp2", 0)],
            "tp3": [signal.get("tp3", 0)],
            "sl": [signal.get("sl", 0)],
            "confidence": [signal.get("confidence", 0)],
            "trade_type": [signal.get("trade_type", "")],
            "timestamp": [timestamp],
            "tp1_possibility": [signal.get("tp1_possibility", 0)],
            "tp2_possibility": [signal.get("tp2_possibility", 0)],
            "tp3_possibility": [signal.get("tp3_possibility", 0)],
            "indicators_used": [signal.get("indicators_used", "")],
            "backtest_result": [signal.get("backtest_result", 0)],
            "volume": [signal.get("volume", 0)],
            "status": ["pending"]
        })

        if os.path.exists(csv_path):
            old_df = pl.read_csv(csv_path)
            if not data.is_empty():
                data = old_df.vstack(data)

        if not data.is_empty():
            data.write_csv(csv_path)
            log(f"Signal logged to CSV for {signal.get('symbol', '')}")
        else:
            log("No valid data to log to CSV", level='ERROR')

        # Archive old logs weekly
        archive_old_logs(csv_path)

    except Exception as e:
        log(f"Error logging signal to CSV: {e}", level='ERROR')

def archive_old_logs(csv_path):
    try:
        if not os.path.exists(csv_path):
            return
        df = pl.read_csv(csv_path)
        if df.is_empty():
            return
        
        current_date = datetime.now(pytz.timezone('Asia/Karachi'))
        week_ago = current_date - pd.Timedelta(days=7)
        old_data = df.filter(pl.col("timestamp").cast(pl.DateTime).dt.date() < week_ago.date())
        
        if not old_data.is_empty():
            archive_path = f"logs/archive/signals_log_{week_ago.strftime('%Y%m%d')}.csv"
            os.makedirs(os.path.dirname(archive_path), exist_ok=True)
            old_data.write_csv(archive_path)
            new_data = df.filter(pl.col("timestamp").cast(pl.DateTime).dt.date() >= week_ago.date())
            new_data.write_csv(csv_path)
            log(f"Archived {len(old_data)} old signals to {archive_path}", level='INFO')
    except Exception as e:
        log(f"Error archiving logs: {e}", level='ERROR')
