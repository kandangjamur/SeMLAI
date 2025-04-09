import os
import pandas as pd
import time
from datetime import datetime, timedelta
from core.analysis import fetch_ohlcv, calculate_indicators, score_signal
from utils.logger import log
from binance.spot import Spot

client = Spot()

# Configurations
TIMEFRAMES = {
    '15m': '15m',
    '30m': '30m',
    '1h': '1h',
    '4h': '4h'
}

PROFIT_TARGET = 0.03  # 3%
LOOKAHEAD_CANDLES = 12  # How many future candles to check after signal (depends on timeframe)
MIN_YEARS = 1


def run_backtest():
    symbols = [s['symbol'] for s in client.exchange_info()['symbols'] if s['symbol'].endswith('USDT') and s['status'] == 'TRADING']
    results = []

    for symbol in symbols:
        log(f"\n🔍 Running backtest for {symbol}...")
        for tf_label, interval in TIMEFRAMES.items():
            try:
                df = fetch_ohlcv(symbol, interval, limit=1500)  # 1500 candles per pair per TF (~1 year+)
                if df is None or len(df) < 100:
                    continue

                signals, wins, losses, total_conf = 0, 0, 0, 0.0

                for i in range(50, len(df) - LOOKAHEAD_CANDLES):
                    sliced_df = df.iloc[:i].copy()
                    indicators = calculate_indicators(sliced_df)
                    score, confidence, _ = score_signal(indicators)

                    if score >= 4:
                        signals += 1
                        total_conf += confidence
                        entry_price = df.iloc[i]['close']

                        future_high = df.iloc[i+1:i+1+LOOKAHEAD_CANDLES]['high'].max()
                        profit = (future_high - entry_price) / entry_price

                        if profit >= PROFIT_TARGET:
                            wins += 1
                        else:
                            losses += 1

                if signals > 0:
                    win_rate = round((wins / signals) * 100, 2)
                    avg_conf = round((total_conf / signals), 2)
                    results.append({
                        'symbol': symbol,
                        'timeframe': tf_label,
                        'signals': signals,
                        'wins': wins,
                        'losses': losses,
                        'win_rate': win_rate,
                        'avg_conf': avg_conf
                    })

                    log(f"📊 [{symbol} - {tf_label}] Signals: {signals}, Wins: {wins}, Losses: {losses}, Win Rate: {win_rate}%, Avg Confidence: {avg_conf}%")

            except Exception as e:
                log(f"❌ Error backtesting {symbol} {tf_label}: {e}")

    df_results = pd.DataFrame(results)
    df_results.to_csv("backtest_results.csv", index=False)
    log("\n✅ Backtest completed and saved to backtest_results.csv")
