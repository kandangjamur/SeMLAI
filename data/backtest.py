import pandas as pd
from core.indicators import calculate_indicators
from model.predictor import predict_trend
import ccxt
from utils.logger import log

def run_backtest():
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    symbols = [s for s in markets if "/USDT" in s and "UP" not in s and "DOWN" not in s]

    results = []

    for symbol in symbols[:30]:  # limit for demo
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=200)
            for i in range(50, len(ohlcv)-1):
                subset = ohlcv[i-50:i]
                signal = calculate_indicators(symbol, subset)
                if not signal:
                    continue
                signal["prediction"] = predict_trend(symbol, subset)
                entry = signal["price"]
                highs = [c[2] for c in ohlcv[i+1:i+10]]
                lows = [c[3] for c in ohlcv[i+1:i+10]]

                status = "pending"
                if signal["tp3"] <= max(highs):
                    status = "tp3"
                elif signal["tp2"] <= max(highs):
                    status = "tp2"
                elif signal["tp1"] <= max(highs):
                    status = "tp1"
                elif signal["sl"] >= min(lows):
                    status = "sl"

                results.append({
                    "symbol": symbol,
                    "confidence": signal["confidence"],
                    "type": signal["trade_type"],
                    "prediction": signal["prediction"],
                    "tp1": signal["tp1"],
                    "tp2": signal["tp2"],
                    "tp3": signal["tp3"],
                    "sl": signal["sl"],
                    "status": status
                })
        except Exception as e:
            log(f"Backtest Error: {symbol} -> {e}")

    df = pd.DataFrame(results)
    df.to_csv("logs/backtest_results.csv", index=False)
    log("📈 Backtest complete.")
