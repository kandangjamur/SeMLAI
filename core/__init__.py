# core/__init__.py

# This file can be left empty or used to import all the necessary components
# from different modules inside the core directory.

from .analysis import analyze_all_symbols
from .indicators import get_rsi, get_macd, get_ema
from .news_sentiment import fetch_news_impact
from .whale_detector import check_whale_activity
from .trade_classifier import classify_trade
