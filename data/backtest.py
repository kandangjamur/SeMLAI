import ccxt
import time
import os
import pandas as pd
from datetime import datetime, timedelta
from core.indicators import calculate_indicators
from model.predictor import predict_trend
from core.trade_classifier import classify_trade
from core.whale_detector import whale_check
from core.news_sentiment import get_sentiment_boost
from utils.logger import log

def backtest():
    exchange = ccxt.binance()
    symbols = [s for s in exchange.load_markets() if '/USDT' in s]

    result = []

    for symbol in symbols:
        log(f"📊 Backtesting {symbol}")
        try:
            since = exchange.parse8601((datetime.utcnow() - timedelta(days=365)).isoformat())
            candles = exchange.fetch_ohlcv(symbol, '1h', since=since, limit=500)

            for i in range(100, len(candles)):
                subset = candles[i-100:i]
                signal = calculate_indicators(symbol, subset)
                if not signal:
                    continue

                sentiment_boost = get_sentiment_boost(symbol)
                signal['confidence'] += sentiment_boost

                if signal['confidence'] < 85:
                    continue

                prediction = predict_trend(symbol, subset)
                signal['prediction'] = prediction
                signal['trade_type'] = classify_trade(signal)

                # Assume entry = close price of last candle
                entry = subset[-1][4]
                direction = prediction
                tp1 = entry * 1.03 if direction == "LONG" else entry * 0.97
                tp2 = entry * 1.05 if direction == "LONG" else entry * 0.95
                tp3 = entry * 1.07 if direction == "LONG" else entry * 0.93
                sl = entry * 0.97 if direction == "LONG" else entry * 1.03

                # Simulate next 10 candles
                future = candles[i:i+10]
                hit = "NONE"
                for f in future:
                    high = f[2]
                    low = f[3]

                    if direction == "LONG":
                        if high >= tp3:
                            hit = "TP3"; break
                        elif high >= tp2:
                            hit = "TP2"; break
                        elif high >= tp1:
                            hit = "TP1"; break
                        elif low <= sl:
                            hit = "SL"; break
                    else:
                        if low <= tp3:
                            hit = "TP3"; break
                        elif low <= tp2:
                            hit = "TP2"; break
                        elif low <= tp1:
                            hit = "TP1"; break
                        elif high >= sl:
                            hit = "SL"; break

                result.append({
                    "symbol": symbol,
                    "direction": direction,
                    "confidence": signal['confidence'],
                    "result": hit,
                    "datetime": datetime.fromtimestamp(subset[-1][0] / 1000).strftime("%Y-%m-%d %H:%M")
                })

        except Exception as e:
            log(f"❌ Backtest error on {symbol}: {e}")
            continue

    df = pd.DataFrame(result)
    os.makedirs("logs", exist_ok=True)
    df.to_csv("logs/backtest_results.csv", index=False)
    log("✅ Backtest complete. Results saved to logs/backtest_results.csv")

if __name__ == "__main__":
    backtest()
# Placeholder for backtest engine
