import os
import time
import ccxt
from core.analysis import calculate_indicators
from core.engine import predict_trend
from utils.logger import log, log_signal_to_csv
from telebot.bot import send_signal
from data.tracker import update_signal_status

exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

symbols = [s['symbol'] for s in exchange.load_markets().values() if s['quote'] == 'USDT' and not s['symbol'].endswith('UP/USDT') and not s['symbol'].endswith('DOWN/USDT')]

sent_signals = {}

while True:
    log("🔁 New Scan Cycle")
    for symbol in symbols:
        try:
            log(f"🔍 Scanning: {symbol}")
            ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
            if not ohlcv or len(ohlcv) < 50:
                continue

            ticker = exchange.fetch_ticker(symbol)
            if ticker.get("baseVolume", 0) < 120000:
                log(f"⚠️ Skipped {symbol} - Low volume")
                continue

            signal = calculate_indicators(symbol, ohlcv)
            if not signal:
                continue

            direction = predict_trend(symbol, ohlcv)
            signal["prediction"] = direction

            # Dynamic TP possibilities
            price = signal["price"]
            signal["tp1_possibility"] = round(max(70, 100 - abs(signal["tp1"] - price) / price * 100), 2)
            signal["tp2_possibility"] = round(max(60, 95 - abs(signal["tp2"] - price) / price * 100), 2)
            signal["tp3_possibility"] = round(max(50, 90 - abs(signal["tp3"] - price) / price * 100), 2)

            signal["confidence"] = min(signal["confidence"], 100)

            if signal["confidence"] >= 75:
                log_signal_to_csv(signal)
                send_signal(signal)
                sent_signals[symbol] = time.time()
                log(f"✅ Signal sent: {symbol} ({signal['confidence']}%)")

        except Exception as e:
            log(f"❌ Error for {symbol}: {e}")

    update_signal_status()
    time.sleep(120)
