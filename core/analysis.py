import time
import ccxt
from core.indicators import calculate_indicators
from core.trade_classifier import classify_trade
from core.whale_detector import whale_check
from model.predictor import predict_trend
from telebot.bot import send_signal
from utils.logger import log, log_signal_to_csv
from core.news_sentiment import get_sentiment_boost

# Store last sent signal times
sent_signals = {}

def run_analysis_loop():
    log("📊 Starting Market Scan")
    exchange = ccxt.binance()
    markets = exchange.load_markets()

    # Temporarily remove volume filter for full scan
    symbols = [s for s in markets if '/USDT' in s]
    log(f"🔢 Total USDT Pairs Loaded: {len(symbols)}")

    while True:
        try:
            log("🔁 Starting new scan cycle")
            for symbol in symbols:
                log(f"🔍 Scanning: {symbol}")

                # Fetch historical candles
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
                except Exception as e:
                    log(f"⚠️ Failed to fetch candles for {symbol}: {e}")
                    continue

                # Calculate indicators
                signal = calculate_indicators(symbol, ohlcv)
                if not signal:
                    log(f"⛔ No signal for {symbol}")
                    continue

                # Apply sentiment boost if trending
                sentiment_boost = get_sentiment_boost(symbol)
                signal['confidence'] += sentiment_boost

                # Filter by confidence
                if signal['trade_type'] == "Scalping" and signal['confidence'] < 75:
                    log(f"⏩ Skipped {symbol} (Scalping < 75%)")
                    continue
                elif signal['confidence'] < 85:
                    log(f"⏩ Skipped {symbol} (< 85% Confidence)")
                    continue

                # Prevent duplicate signal within 30 min
                now = time.time()
                if symbol in sent_signals and now - sent_signals[symbol] < 1800:
                    log(f"🔁 Skipped duplicate: {symbol}")
                    continue

                # Check whale volume
                if not whale_check(symbol, exchange):
                    log(f"🐋 No whale activity: {symbol}")
                    continue

                # Predict trend
                signal['prediction'] = predict_trend(symbol, ohlcv)

                # Classify trade
                signal['trade_type'] = classify_trade(signal)

                # Enforce LONG only for Spot trades
                if signal['trade_type'] == "Spot":
                    signal['prediction'] = "LONG"

                # Save send timestamp
                sent_signals[symbol] = now

                # Log and send
                log_signal_to_csv(signal)
                log(f"✅ Signal: {symbol} | {signal['trade_type']} | {signal['prediction']} | {signal['confidence']}%")
                send_signal(signal)

        except Exception as e:
            log(f"❌ Analysis Error: {e}")

        log("⏳ Waiting 2 min before next scan cycle...")
        time.sleep(120)
