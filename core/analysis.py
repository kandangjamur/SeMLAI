import time
import ccxt
from core.indicators import calculate_indicators
from core.trade_classifier import classify_trade
from core.whale_detector import whale_check
from model.predictor import predict_trend
from telebot.bot import send_signal
from utils.logger import log, log_signal_to_csv
from core.news_sentiment import get_sentiment_boost

sent_signals = {}

def run_analysis_loop():
    log("📊 Starting Market Scan")
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    symbols = [s for s in markets if '/USDT' in s and ':' not in s]
    log(f"🔢 Total USDT Pairs Loaded: {len(symbols)}")

    while True:
        try:
            log("🔁 Starting new scan cycle")
            for symbol in symbols:
                log(f"🔍 Scanning: {symbol}")
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
                except Exception as e:
                    log(f"⚠️ Failed to fetch candles for {symbol}: {e}")
                    continue

                signal = calculate_indicators(symbol, ohlcv)
                if not signal:
                    log(f"⛔ No signal for {symbol}")
                    continue

                sentiment_boost = get_sentiment_boost(symbol)
                signal['confidence'] += sentiment_boost
                signal['trade_type'] = classify_trade(signal)

                log(f"📈 Confidence: {signal['confidence']}% | Type: {signal['trade_type']}")

                if signal['trade_type'] == "Scalping" and signal['confidence'] < 75:
                    continue
                elif signal['confidence'] < 85:
                    continue

                now = time.time()
                if symbol in sent_signals and now - sent_signals[symbol] < 1800:
                    continue

                if not whale_check(symbol, exchange):
                    log(f"🐋 No whale activity: {symbol}")
                    continue

                signal['prediction'] = predict_trend(symbol, ohlcv)
                if signal['trade_type'] == "Spot":
                    signal['prediction'] = "LONG"

                sent_signals[symbol] = now
                log_signal_to_csv(signal)
                log(f"✅ Signal: {symbol} | {signal['trade_type']} | {signal['prediction']} | {signal['confidence']}%")
                send_signal(signal)

        except Exception as e:
            log(f"❌ Analysis Error: {e}")

        log("⏳ Waiting 2 min before next scan cycle...")
        time.sleep(120)
