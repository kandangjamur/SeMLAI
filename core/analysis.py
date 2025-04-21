import time
import ccxt
from core.indicators import calculate_indicators
from model.predictor import predict_trend
from telebot.bot import send_signal
from utils.logger import log, log_signal_to_csv
from data.tracker import update_signal_status

sent_signals = {}

def run_analysis_loop():
    log("📊 Starting Market Scan")
    exchange = ccxt.binance()
    symbols = [s for s in exchange.load_markets() if "/USDT" in s]

    while True:
        log("🔁 New Scan Cycle")
        for symbol in symbols:
            log(f"🔍 Scanning: {symbol}")
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
                signal = calculate_indicators(symbol, ohlcv)
                if not signal:
                    continue

                if symbol in sent_signals and time.time() - sent_signals[symbol] < 1800:
                    continue

                signal['prediction'] = predict_trend(symbol, ohlcv)
                log_signal_to_csv(signal)
                send_signal(signal)
                sent_signals[symbol] = time.time()
                log(f"✅ Signal sent: {symbol} ({signal['confidence']}%)")

            except Exception as e:
                log(f"❌ Error for {symbol}: {e}")

        update_signal_status()
        time.sleep(120)

def run_analysis_once():
    exchange = ccxt.binance()
    symbols = [s for s in exchange.load_markets() if "/USDT" in s]
    for symbol in symbols[:20]:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
            signal = calculate_indicators(symbol, ohlcv)
            if not signal:
                continue
            signal['prediction'] = predict_trend(symbol, ohlcv)
            log_signal_to_csv(signal)
            send_signal(signal)
        except Exception as e:
            log(f"❌ Manual Scan Error: {symbol} -> {e}")
