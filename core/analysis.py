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

    # Filtering symbols with '/USDT' in the name and quoteVolume > 1 million
    symbols = [s for s in markets if '/USDT' in s and markets[s].get('quoteVolume', 0) > 1_000_000]
    log(f"🔢 Total USDT Pairs Loaded: {len(symbols)}")

    while True:
        try:
            log("🔁 Starting new scan cycle")
            for symbol in symbols:
                log(f"🔍 Scanning: {symbol}")

                try:
                    # Fetching OHLCV data for 15-minute intervals (recent 100 candles)
                    ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)

                    # Running indicator calculations
                    signal = calculate_indicators(symbol, ohlcv)

                    # If no signal is generated, skip the pair
                    if not signal:
                        log(f"⛔ No valid setup found for {symbol}")
                        continue

                    # Adding sentiment boost to the confidence
                    sentiment_boost = get_sentiment_boost(symbol)
                    signal['confidence'] += sentiment_boost

                    # Logging the score and confidence
                    log(f"📈 Score: {signal.get('score', '-')}/6 | Confidence: {signal['confidence']}%")

                    # Filtering based on confidence
                    if signal['trade_type'] == "Scalping" and signal['confidence'] < 75:
                        log(f"⚠️ Skipping {symbol} (Scalping < 75%)")
                        continue
                    elif signal['confidence'] < 85:
                        log(f"⚠️ Skipping {symbol} (< 85% Confidence)")
                        continue

                    # Preventing duplicate signals within 30 minutes
                    now = time.time()
                    if symbol in sent_signals and now - sent_signals[symbol] < 1800:
                        log(f"🔁 Skipped recent signal for {symbol}")
                        continue

                    # Checking for whale activity
                    if not whale_check(symbol, exchange):
                        log(f"🐋 No whale confirmation for {symbol}")
                        continue

                    # Predicting trend based on the signal
                    signal['prediction'] = predict_trend(symbol, ohlcv)

                    # Classifying the trade type based on the signal
                    signal['trade_type'] = classify_trade(signal)

                    # Defaulting to 'LONG' for Spot trades
                    if signal['trade_type'] == "Spot":
                        signal['prediction'] = "LONG"

                    # Marking the signal as sent and saving it
                    sent_signals[symbol] = now
                    log_signal_to_csv(signal)

                    # Logging and sending the signal to Telegram
                    log(f"✅ Signal SENT: {symbol} | {signal['trade_type']} | {signal['prediction']} | {signal['confidence']}%")
                    send_signal(signal)

                except Exception as single_error:
                    log(f"❌ Error scanning {symbol}: {single_error}")

        except Exception as loop_error:
            log(f"❌ Analysis Loop Error: {loop_error}")

        # Delay between scan cycles
        log("⏳ Waiting 2 min before next scan cycle...\n")
        time.sleep(120)
