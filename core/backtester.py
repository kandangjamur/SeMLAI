import ccxt
import pandas as pd
from core.indicators import calculate_indicators
from model.predictor import predict_trend
from utils.logger import log
import os

def run_backtest_report():
    log("📈 Starting Backtest...")
    exchange = ccxt.binance()
    symbols = [s for s in exchange.load_markets() if "/USDT" in s]
    results = []

    for symbol in symbols[:50]:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
            signal = calculate_indicators(symbol, ohlcv)
            if not signal:
                continue

            prediction = predict_trend(symbol, ohlcv)
            close = ohlcv[-1][4]

            # Simplistic win check for TP1
            win = False
            if prediction == "LONG":
                win = close >= signal['tp1']
            elif prediction == "SHORT":
                win = close <= signal['tp1']

            results.append({
                "symbol": symbol,
                "prediction": prediction,
                "confidence": signal["confidence"],
                "win": win,
            })

        except Exception as e:
            log(f"❌ Backtest error for {symbol}: {e}")
            continue

    df = pd.DataFrame(results)
    os.makedirs("logs", exist_ok=True)
    df.to_csv("logs/backtest_results.csv", index=False)
    log("📊 Backtest complete. Results saved to logs/backtest_results.csv")
