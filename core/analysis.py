import time
import ccxt
from core.indicators import calculate_indicators
from model.predictor import predict_trend
from telebot.bot import send_signal
from utils.logger import log, log_signal_to_csv
from core.news_sentiment import get_sentiment_boost
from core.whale_detector import whale_check

sent_signals = {}

def run_analysis_loop():
    log("📊 Starting Market Scan")
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    symbols = [s for s in markets if "/USDT" in s]
    log(f"🔢 Total USDT Pairs Loaded: {len(symbols)}")

    while True:
        try:
            log("🔁 Starting new scan cycle")
            for symbol in symbols:
                log(f"🔍 Scanning: {symbol}")
                try:
                    ohlcv_15m = exchange.fetch_ohlcv(symbol, '15m', limit=100)
                    ohlcv_1h = exchange.fetch_ohlcv(symbol, '1h', limit=100)
                    ohlcv_4h = exchange.fetch_ohlcv(symbol, '4h', limit=100)
                except Exception as e:
                    log(f"⚠️ Failed to fetch candles for {symbol}: {e}")
                    continue

                signal = calculate_indicators(symbol, ohlcv_15m, ohlcv_1h, ohlcv_4h)
                if not signal:
                    log(f"⛔ No signal for {symbol}")
                    continue

                signal['confidence'] += get_sentiment_boost(symbol)

                if signal['trade_type'] == "Scalping" and signal['confidence'] < 60:
                    log(f"⏩ Skipped {symbol} (Scalping < 60%)")
                    continue
                elif signal['trade_type'] == "Normal" and signal['confidence'] < 75:
                    log(f"⏩ Skipped {symbol} (Normal < 75%)")
                    continue

                now = time.time()
                if symbol in sent_signals and now - sent_signals[symbol] < 1800:
                    log(f"🔁 Skipped duplicate: {symbol}")
                    continue

                if not whale_check(symbol, exchange):
                    log(f"🐋 No whale activity: {symbol}")
                    continue

                try:
                    signal['prediction'] = predict_trend(symbol, ohlcv_15m)
                    price = signal['price']
                    atr = signal.get('atr', 0.01)

                    if signal['prediction'] == "LONG":
                        signal['tp1'] = round(price + atr * 1.5, 4)
                        signal['tp2'] = round(price + atr * 2.5, 4)
                        signal['tp3'] = round(price + atr * 4, 4)
                        signal['sl'] = round(price - atr * 1.5, 4)
                    else:
                        signal['tp1'] = round(price - atr * 1.5, 4)
                        signal['tp2'] = round(price - atr * 2.5, 4)
                        signal['tp3'] = round(price - atr * 4, 4)
                        signal['sl'] = round(price + atr * 1.5, 4)

                except Exception as e:
                    log(f"⚠️ Trend prediction error for {symbol}: {e}")
                    continue

                sent_signals[symbol] = now
                log_signal_to_csv(signal)
                log(f"✅ Signal: {symbol} | {signal['trade_type']} | {signal['prediction']} | {signal['confidence']}%")
                send_signal(signal)

        except Exception as e:
            log(f"❌ Analysis Error: {e}")

        log("⏳ Waiting 2 min before next scan cycle...")
        time.sleep(120)
