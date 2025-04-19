import ccxt
import pandas as pd
from core.indicators import calculate_indicators
from model.predictor import predict_trend
from datetime import datetime
from utils.logger import log
import time

def run_backtest():
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    usdt_pairs = [s for s in markets if "/USDT" in s]

    result_logs = []

    for symbol in usdt_pairs:
        try:
            log(f"📊 Backtesting: {symbol}")
            df = exchange.fetch_ohlcv(symbol, '1h', limit=500)
            win_count = 0
            total_signals = 0

            for i in range(50, len(df) - 3):
                candles = df[i-50:i]
                signal = calculate_indicators(symbol, candles)
                if not signal or signal['confidence'] < 60:
                    continue

                signal['prediction'] = predict_trend(symbol, candles)
                entry = signal['price']
                tp1 = entry * (1.01 if signal['prediction'] == "LONG" else 0.99)
                sl = entry * (0.98 if signal['prediction'] == "LONG" else 1.02)
                next_candles = df[i+1:i+4]
                prices = [c[4] for c in next_candles]

                if signal['prediction'] == "LONG" and any(p >= tp1 for p in prices):
                    win_count += 1
                elif signal['prediction'] == "SHORT" and any(p <= tp1 for p in prices):
                    win_count += 1

                total_signals += 1

            if total_signals > 0:
                winrate = round((win_count / total_signals) * 100, 2)
                result_logs.append(f"{symbol}: {winrate}% ({win_count}/{total_signals})")

        except Exception as e:
            log(f"⚠️ Backtest error: {e}")
            continue

    with open("logs/backtest_results.txt", "w") as f:
        f.write("\n".join(result_logs))

    log("✅ Backtest complete.")
