# core/analysis.py
import time
import ccxt
from core.indicators import calculate_indicators
from core.multi_timeframe import multi_timeframe_boost
from model.predictor import predict_trend
from telebot.bot import send_signal
from utils.logger import log, log_signal_to_csv
from data.tracker import update_signal_status

blacklist = ["BULL", "BEAR", "2X", "3X", "5X", "DOWN", "UP", "ETF"]
sent_signals = {}

def is_blacklisted(symbol):
    return any(term in symbol for term in blacklist)

def log_debug_info(signal):
    log(f"📌 AUDIT LOG — {signal['symbol']}")
    log(f"Confidence: {signal['confidence']}% | TP1: {signal['tp1']} | TP2: {signal['tp2']} | TP3: {signal['tp3']} | SL: {signal['sl']}")
    log(f"TP chances => TP1: {signal['tp1_chance']}% | TP2: {signal['tp2_chance']}% | TP3: {signal['tp3_chance']}%")
    log(f"Leverage: {signal['leverage']}x | Prediction: {signal['prediction']}")

def run_analysis_loop():
    log("📊 Starting Market Scan")
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    symbols = [s for s in markets if "/USDT" in s and not is_blacklisted(s)]

    while True:
        log("🔁 New Scan Cycle")
        for symbol in symbols:
            log(f"🔍 Scanning: {symbol}")
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
                if not ohlcv or len(ohlcv) < 50:
                    continue

                ticker = exchange.fetch_ticker(symbol)
                if ticker.get("baseVolume", 0) < 100000:
                    log(f"⚠️ Skipped {symbol} - Low volume")
                    continue

                signal = calculate_indicators(symbol, ohlcv)
                if not signal:
                    continue

                direction = predict_trend(symbol, ohlcv)
                signal["prediction"] = direction

                buffer = signal["atr"] * 1.5
                price = signal["price"]
                support = signal["support"]
                resistance = signal["resistance"]

                if direction == "LONG" and resistance and resistance - price > buffer:
                    signal["confidence"] += 5
                elif direction == "SHORT" and support and price - support > buffer:
                    signal["confidence"] += 5
                else:
                    continue

                mtf_boost = multi_timeframe_boost(symbol, exchange, direction)
                signal["confidence"] += mtf_boost

                if signal["confidence"] < 75:
                    continue

                if symbol in sent_signals and time.time() - sent_signals[symbol] < 900:
                    continue

                log_debug_info(signal)
                log_signal_to_csv(signal)
                send_signal(signal)
                sent_signals[symbol] = time.time()

            except Exception as e:
                log(f"❌ Error for {symbol}: {e}")

        update_signal_status()
        time.sleep(120)
