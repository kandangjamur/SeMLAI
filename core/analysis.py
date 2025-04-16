import time
import ccxt
from core.indicators import calculate_indicators
from core.trade_classifier import classify_trade
from core.whale_detector import whale_check
from model.predictor import predict_trend
from telebot.bot import send_signal
from utils.logger import log, log_signal_to_csv
from core.news_sentiment import get_sentiment_boost, fetch_trending_coins

# Store last sent signal times
sent_signals = {}

def run_analysis_loop():
    log("📊 Starting Market Scan")
    exchange = ccxt.binance()
    markets = exchange.load_markets()

    # ✅ Trending + All Binance USDT Pairs
    all_symbols = [s for s in markets if '/USDT' in s]
    trending = fetch_trending_coins()
    log(f"[TRENDING] {trending}")
    symbols = list(set(all_symbols + trending))  # ✅ Merge and remove duplicates
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

                # Add sentiment confidence boost
                sentiment_boost = get_sentiment_boost(symbol)
                signal['confidence'] += sentiment_boost

                # 🧠 Classify trade before confidence filter
                signal['trade_type'] = classify_trade(signal)

                # Confidence-based filtering
                if signal['trade_type'] == "Scalping" and signal['confidence'] < 60:
                    log(f"⏩ Skipped {symbol} (Scalping < 60%)")
                    continue
                elif signal['confidence'] < 70:
                    log(f"⏩ Skipped {symbol} (< 70% Confidence)")
                    continue

                # Skip duplicate signals (30 min window)
                now = time.time()
                if symbol in sent_signals and now - sent_signals[symbol] < 1800:
                    log(f"🔁 Skipped duplicate: {symbol}")
                    continue

                # Whale volume check
                if not whale_check(symbol, exchange):
                    log(f"🐋 No whale activity: {symbol}")
                    continue

                # Trend prediction
                signal['prediction'] = predict_trend(symbol, ohlcv)

                # Spot trades always LONG
                if signal['trade_type'] == "Spot":
                    signal['prediction'] = "LONG"

                # Save time & log
                sent_signals[symbol] = now
                log_signal_to_csv(signal)
                log(f"✅ Signal: {symbol} | {signal['trade_type']} | {signal['prediction']} | {signal['confidence']}%")

                # Send signal
                send_signal(signal)

        except Exception as e:
            log(f"❌ Analysis Error: {e}")

        log("⏳ Waiting 2 min before next scan cycle...")
        time.sleep(120)
