from utils.logger import log

def predict_trend(symbol, exchange):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe="15m", limit=50)
        if len(ohlcv) < 3:
            log(f"⚠️ Insufficient data for trend prediction for {symbol}")
            return None

        closes = [x[4] for x in ohlcv]
        if closes[-1] > closes[-2] > closes[-3]:
            log(f"✅ LONG trend detected for {symbol}")
            return "LONG"
        elif closes[-1] < closes[-2] < closes[-3]:
            log(f"✅ SHORT trend detected for {symbol}")
            return "SHORT"
        log(f"⚠️ No clear trend for {symbol}")
        return None  # کوئی ٹرینڈ نہ ہو تو None واپس کریں
    except Exception as e:
        log(f"❌ Error predicting trend for {symbol}: {e}")
        return None
