import ccxt, csv, os
from core.indicators import calculate_indicators
from model.predictor import predict_trend

def run_backtest_report():
    exchange = ccxt.binance()
    symbols = [s for s in exchange.load_markets() if "/USDT" in s]
    with open("logs/backtest_results.csv", "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Symbol", "Confidence", "Prediction", "TP1", "TP2", "TP3", "SL"])

        for symbol in symbols[:50]:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, "15m", limit=100)
                signal = calculate_indicators(symbol, ohlcv)
                if not signal: continue

                signal["prediction"] = predict_trend(symbol, ohlcv)
                writer.writerow([
                    signal["symbol"], signal["confidence"], signal["prediction"],
                    signal["tp1"], signal["tp2"], signal["tp3"], signal["sl"]
                ])
            except Exception as e:
                continue
