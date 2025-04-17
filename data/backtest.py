
import os
import ccxt
import time
import pandas as pd
from datetime import datetime
from core.indicators import calculate_indicators  # Must support multi-timeframe logic
from model.predictor import predict_trend
from core.trade_classifier import classify_trade

# Directory to store logs
os.makedirs("logs", exist_ok=True)
results_file = "logs/backtest_results.csv"

# Initialize exchange
exchange = ccxt.binance()
markets = exchange.load_markets()
symbols = [s for s in markets if "/USDT" in s and not s.endswith("DOWN/USDT") and not s.endswith("UP/USDT")]

# Define timeframes to test
timeframes = ["15m", "1h", "4h"]

# Utility to evaluate TP hits
def evaluate_tp_sl(entry_price, candles, tp1, tp2, tp3, sl, direction):
    for candle in candles:
        high, low = candle[2], candle[3]
        if direction == "LONG":
            if low <= sl:
                return "SL"
            elif high >= tp3:
                return "TP3"
            elif high >= tp2:
                return "TP2"
            elif high >= tp1:
                return "TP1"
        elif direction == "SHORT":
            if high >= sl:
                return "SL"
            elif low <= tp3:
                return "TP3"
            elif low <= tp2:
                return "TP2"
            elif low <= tp1:
                return "TP1"
    return "None"

# Open CSV writer
with open(results_file, "w") as f:
    f.write("symbol,timeframe,direction,confidence,result,tp1,tp2,tp3,sl
")

# Run backtest
for symbol in symbols:
    print(f"🔍 Backtesting: {symbol}")
    for tf in timeframes:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=150)
            if len(ohlcv) < 100:
                continue

            signal = calculate_indicators(symbol, ohlcv)
            if not signal:
                continue

            signal["prediction"] = predict_trend(symbol, ohlcv)
            signal["trade_type"] = classify_trade(signal)
            confidence = signal["confidence"]

            if signal["trade_type"] == "Spot":
                continue  # Spot disabled

            # Generate TP/SL
            price = signal["price"]
            tp1 = round(price * (1.01 if signal["prediction"] == "LONG" else 0.99), 3)
            tp2 = round(price * (1.03 if signal["prediction"] == "LONG" else 0.97), 3)
            tp3 = round(price * (1.05 if signal["prediction"] == "LONG" else 0.95), 3)
            sl = round(price * (0.98 if signal["prediction"] == "LONG" else 1.02), 3)

            outcome = evaluate_tp_sl(price, ohlcv[-10:], tp1, tp2, tp3, sl, signal["prediction"])

            with open(results_file, "a") as f:
                f.write(f"{symbol},{tf},{signal['prediction']},{confidence},{outcome},{tp1},{tp2},{tp3},{sl}
")

            time.sleep(0.5)

        except Exception as e:
            print(f"⚠️ Error on {symbol}-{tf}: {e}")
            continue

print("✅ Backtest Completed: logs/backtest_results.csv")
