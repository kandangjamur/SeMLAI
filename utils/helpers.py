import pandas as pd
import numpy as np
from datetime import datetime

def normalize_value(val, min_val, max_val):
    """Normalize a value between 0 and 1."""
    if max_val - min_val == 0:
        return 0
    return (val - min_val) / (max_val - min_val)

def calculate_price_change(open_price, close_price):
    """Calculate price change percentage."""
    return ((close_price - open_price) / open_price) * 100

def sentiment_to_score(sentiment):
    """Convert sentiment label to score."""
    mapping = {
        'Bullish': 1.0,
        'Neutral': 0.0,
        'Bearish': -1.0
    }
    return mapping.get(sentiment, 0.0)

def timestamp_to_str(ts):
    """Convert timestamp to formatted string."""
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

def safe_float(val):
    """Safely convert value to float."""
    try:
        return float(val)
    except:
        return 0.0
