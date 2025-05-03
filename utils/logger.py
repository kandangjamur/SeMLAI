import logging
import os

def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        os.makedirs("logs", exist_ok=True)
        file_handler = logging.FileHandler(f"logs/{name}.log")
        stream_handler = logging.StreamHandler()

        formatter = logging.Formatter('[%(asctime)s] %(message)s', "%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    return logger
