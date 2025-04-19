import ccxt
import pandas as pd
from core.indicators import calculate_indicators
from model.predictor import predict_trend
from utils.logger import log
import os

def run_backtest_report():
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    symbols = [s for s in markets if "/USDT" in s and not s.endswith("UP/USDT") and not s.endswith("DOWN/USDT")]

    results = []
    for symbol in symbols:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=150)
            signal = calculate_indicators(symbol, ohlcv)
            if not signal or signal["confidence"] < 75:
                continue

            signal["prediction"] = predict_trend(symbol, ohlcv)
            price = signal["price"]
            atr = signal.get("atr", 0)

            # Set TP/SL
            if signal["prediction"] == "LONG":
                tp1 = price + atr * 1.2
                tp2 = price + atr * 2
                tp3 = price + atr * 3
                sl = price - atr * 1.2
            else:
                tp1 = price - atr * 1.2
                tp2 = price - atr * 2
                tp3 = price - atr * 3
                sl = price + atr * 1.2

            closes = [x[4] for x in ohlcv[-10:]]
            hit = "None"
            for close in closes:
                if signal["prediction"] == "LONG":
                    if close >= tp3:
                        hit = "TP3"
                        break
                    elif close >= tp2:
                        hit = "TP2"
                        break
                    elif close >= tp1:
                        hit = "TP1"
                        break
                    elif close <= sl:
                        hit = "SL"
                        break
                else:
                    if close <= tp3:
                        hit = "TP3"
                        break
                    elif close <= tp2:
                        hit = "TP2"
                        break
                    elif close <= tp1:
                        hit = "TP1"
                        break
                    elif close >= sl:
                        hit = "SL"
                        break

            results.append({
                "symbol": symbol,
                "confidence": signal["confidence"],
                "prediction": signal["prediction"],
                "hit": hit,
            })
        except Exception as e:
            log(f"❌ Error backtesting {symbol}: {e}")
            continue

    df = pd.DataFrame(results)
    os.makedirs("logs", exist_ok=True)
    df.to_csv("logs/backtest_results.csv", index=False)
    log("✅ Backtest complete. Saved to logs/backtest_results.csv")
