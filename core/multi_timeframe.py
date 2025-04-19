import ccxt
from model.predictor import predict_trend

def multi_timeframe_boost(symbol):
    exchange = ccxt.binance()
    aligned = 0
    total = 0
    directions = []

    for tf in ["15m", "1h", "4h"]:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=100)
            direction = predict_trend(symbol, ohlcv)
            directions.append(direction)
            total += 1
        except:
            continue

    if directions.count("LONG") >= 2:
        return "LONG", 10  # extra confidence
    elif directions.count("SHORT") >= 2:
        return "SHORT", 10
    else:
        return "SIDEWAY", 0
