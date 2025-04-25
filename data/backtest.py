import ccxt
import pandas as pd
from core.indicators import calculate_indicators
from model.predictor import predict_trend
from datetime import datetime

def run_backtest():
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    symbols = [s for s in markets if "/USDT" in s and "DOWN" not in s and "UP" not in s]
    results = []

    for symbol in symbols[:30]:
        print(f"⏱ Backtesting: {symbol}")
        try:
            df = exchange.fetch_ohlcv(symbol, '15m', limit=500)
            signals = []

            for i in range(100, len(df), 5):
                sub_df = df[i-100:i]
                signal = calculate_indicators(symbol, sub_df)
                if signal:
                    signal['prediction'] = predict_trend(symbol, sub_df)
                    signals.append(signal)

            for s in signals:
                price = s['price']
                tp1, tp2, tp3, sl = s['tp1'], s['tp2'], s['tp3'], s['sl']
                simulated_prices = [row[4] for row in df[df.index(s['timestamp']):df.index(s['timestamp'])+20]]

                hit = "none"
                for sp in simulated_prices:
                    if sp >= tp1: hit = "tp1"; break
                    elif sp >= tp2: hit = "tp2"; break
                    elif sp >= tp3: hit = "tp3"; break
                    elif sp <= sl: hit = "sl"; break

                results.append({
                    "symbol": symbol,
                    "conf": s['confidence'],
                    "result": hit,
                    "type": s['trade_type']
                })

        except Exception as e:
            print(f"Error: {e}")

    df_out = pd.DataFrame(results)
    df_out.to_csv("logs/backtest_results.csv", index=False)
    print("✅ Backtest complete. Logged to CSV.")
