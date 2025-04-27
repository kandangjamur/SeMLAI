# core/analysis.py
import time
import ccxt
from core.indicators import calculate_indicators
from telegram.bot import send_signal
from utils.logger import log

# Define the multiple timeframes you want to check
TIMEFRAMES = ["15m", "1h", "4h", "1d"]

def run_analysis_loop():
    log("📊 Starting Multi-Timeframe Market Scan...")

    exchange = ccxt.binance()
    markets = exchange.load_markets()
    symbols = [s for s in markets if '/USDT' in s]  # Only USDT pairs

    while True:
        try:
            for symbol in symbols:
                if symbol not in exchange.symbols:
                    log(f"⛔ Skipping {symbol} - Symbol not available on Binance")
                    continue

                timeframe_results = []
                all_signals = {}

                for tf in TIMEFRAMES:
                    try:
                        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
                        if not ohlcv or len(ohlcv) < 50:
                            log(f"⚠️ No sufficient data for {symbol} on {tf}")
                            continue

                        signal = calculate_indicators(symbol, ohlcv)
                        if signal:
                            timeframe_results.append(signal)
                            all_signals[tf] = signal
                        else:
                            all_signals[tf] = None

                    except Exception as tf_error:
                        log(f"❌ Error fetching {symbol} on {tf}: {tf_error}")
                        all_signals[tf] = None

                # Decision logic: How many strong timeframes
                strong_timeframes = [s for s in timeframe_results if s['confidence'] >= 75]

                if len(strong_timeframes) >= 3:
                    main_signal = strong_timeframes[0]  # Use the first strong one (e.g., 15m)

                    log(f"🚀 Signal for {symbol} | Confidence: {main_signal['confidence']}% | Possibility: {main_signal['possibility']}% | Type: {main_signal['trade_type']} | Leverage: {main_signal['leverage']}x")
                    send_signal(main_signal)
                else:
                    log(f"⏭️ Skipped {symbol} - Not enough strong confirmations ({len(strong_timeframes)}/4)")

        except Exception as outer_error:
            log(f"❌ Critical error in analysis loop: {outer_error}")

        time.sleep(300)  # Sleep for 5 minutes before next full scan
