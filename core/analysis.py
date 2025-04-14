import time
import ccxt
from core.indicators import calculate_indicators
from core.trade_classifier import classify_trade
from core.whale_detector import whale_check
from model.predictor import predict_trend
from telegram.bot import send_signal
from utils.logger import log

def run_analysis_loop():
    log("📊 Starting Market Scan")
    exchange = ccxt.binance()
    symbols = [s for s in exchange.load_markets() if '/USDT' in s]
    while True:
        try:
            for symbol in symbols:
                ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
                signal = calculate_indicators(symbol, ohlcv)
                if signal and whale_check(symbol, exchange):
                    signal['prediction'] = predict_trend(symbol, ohlcv)
                    signal['trade_type'] = classify_trade(signal)
                    log(f"✅ Signal: {symbol} | {signal['trade_type']} | {signal['prediction']}")
                    send_signal(signal)
        except Exception as e:
            log(f"❌ Analysis Error: {e}")
        time.sleep(120)
