import ccxt
import pandas as pd
import time
from core.indicators import calculate_indicators
from model.predictor import predict_trend

def run_backtest(timeframes=["15m", "1h", "4h"]):
    exchange = ccxt.binance()
    pairs = [s for s in exchange.load_markets() if "/USDT" in s and ":USDT" not in s]

    results = []

    for symbol in pairs:
        print(f"🔁 Backtesting: {symbol}")
        for tf in timeframes:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=200)
                for i in range(100, len(ohlcv)):
                    slice = ohlcv[i - 100:i]
                    signal = calculate_indicators(symbol, slice)
                    if not signal or signal["confidence"] < 60:
                        continue

                    signal["prediction"] = predict_trend(symbol, slice)
                    entry = signal["price"]

                    if signal["prediction"] == "LONG":
                        tp = entry * 1.03
                        sl = entry * 0.98
                        direction = "LONG"
                    else:
                        tp = entry * 0.97
                        sl = entry * 1.02
                        direction = "SHORT"

                    price_range = [c[4] for c in ohlcv[i:i+5]]  # next 5 candles

                    result = "LOSS"
                    for price in price_range:
                        if direction == "LONG" and price >= tp:
                            result = "WIN"
                            break
                        elif direction == "SHORT" and price <= tp:
                            result = "WIN"
                            break
                        elif (direction == "LONG" and price <= sl) or (direction == "SHORT" and price >= sl):
                            break

                    results.append({
                        "symbol": symbol,
                        "timeframe": tf,
                        "confidence": signal["confidence"],
                        "result": result,
                        "direction": direction
                    })

            except Exception as e:
                print(f"⚠️ Error testing {symbol} @ {tf}: {e}")
                continue

    df = pd.DataFrame(results)
    df.to_csv("logs/backtest_results.csv", index=False)
    print("✅ Backtest complete. Results saved.")
