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

def get_probabilities(conf):
    return {
        "tp1_prob": min(98, conf + 3),
        "tp2_prob": min(90, conf - 2),
        "tp3_prob": min(80, conf - 10)
    }

def log_debug_info(signal):
    log(f"📌 AUDIT LOG — {signal['symbol']}")
    log(f"Confidence: {signal['confidence']}% | Type: {signal['trade_type']} | Prediction: {signal['prediction']}")
    log(f"TP1: {signal['tp1']} | TP2: {signal['tp2']} | TP3: {signal['tp3']} | SL: {signal['sl']}")

def run_analysis_loop():
    log("📊 Starting Market Scan")
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    symbols = [s for s in markets if "/USDT" in s and not is_blacklisted(s)]

    while True:
        log("🔁 New Scan Cycle")
        for symbol in symbols:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
                if not ohlcv or len(ohlcv) < 50:
                    continue

                ticker = exchange.fetch_ticker(symbol)
                if ticker.get("baseVolume", 0) < 150000:
                    continue

                signal = calculate_indicators(symbol, ohlcv)
                if not signal: continue

                direction = predict_trend(symbol, ohlcv)
                signal["prediction"] = direction

                mtf_boost = multi_timeframe_boost(symbol, exchange, direction)
                signal["confidence"] += mtf_boost
                signal.update(get_probabilities(signal["confidence"]))

                if signal["confidence"] < 80:
                    continue

                signal_type_check = signal["tp2"] - signal["price"]
                if signal_type_check < 0.01:
                    continue

                if direction == "LONG" and signal["resistance"] and (signal["resistance"] - signal["price"]) < signal["atr"]:
                    continue
                if direction == "SHORT" and signal["support"] and (signal["price"] - signal["support"]) < signal["atr"]:
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
