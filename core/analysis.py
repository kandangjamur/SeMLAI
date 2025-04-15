import time
import ccxt
from core.indicators import calculate_indicators
from core.trade_classifier import classify_trade
from core.whale_detector import whale_check
from model.predictor import predict_trend
from core.news_sentiment import get_sentiment_boost
from telebot.bot import send_signal
from utils.logger import log, log_signal_to_csv

sent_signals = {}

def run_analysis_loop():
    log("📊 Starting Market Scan")
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    symbols = [
        s for s in markets
        if '/USDT' in s and markets[s].get('quoteVolume', 0) > 1_000_000
    ]

    while True:
        try:
            for symbol in symbols:
                ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
                signal = calculate_indicators(symbol, ohlcv)

                if not signal:
                    continue

                sentiment_boost = get_sentiment_boost(signal['symbol'])
                signal['confidence'] += sentiment_boost

                # 🎯 Filter by type
                if signal['trade_type'] == "Scalping" and signal['confidence'] < 75:
                    log(f"⏩ Skipped (Low Conf - Scalping): {symbol} ({signal['confidence']}%)")
                    continue
                elif signal['confidence'] < 85:
                    log(f"⏩ Skipped (Low Conf): {symbol} ({signal['confidence']}%)")
                    continue

                now = time.time()
                if symbol in sent_signals and now - sent_signals[symbol] < 1800:
                    log(f"🔁 Skipped duplicate signal: {symbol}")
                    continue

                if not whale_check(symbol, exchange):
                    log(f"🐋 Skipped (No whale activity): {symbol}")
                    continue

                signal['prediction'] = predict_trend(symbol, ohlcv)
                signal['trade_type'] = classify_trade(signal)

                if signal['trade_type'] == "Spot":
                    signal['prediction'] = "LONG"

                sent_signals[symbol] = now
                log_signal_to_csv(signal)

                log(f"✅ Signal: {symbol} | {signal['trade_type']} | {signal['prediction']} | {signal['confidence']}%")
                send_signal(signal)

        except Exception as e:
            log(f"❌ Analysis Error: {e}")

        time.sleep(120)
