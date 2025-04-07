import logging
import os

LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "signals.log"),
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

def log_info(msg):
    logging.info(msg)

def log_warning(msg):
    logging.warning(msg)

def log_error(msg):
    logging.error(msg)

def log_success_signal(symbol, data):
    logging.info(f"[SIGNAL] {symbol} | Signal: {data['signal']} | Confidence: {data['confidence']} | TP: {data['tp1']} | SL: {data['sl']}")
