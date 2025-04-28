from core.multi_timeframe import multi_timeframe_boost
from model.predictor import predict_trend
from utils.logger import log

def run_full_engine(signal, symbol, exchange):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
        direction = predict_trend(symbol, ohlcv)
        if direction not in ["LONG", "SHORT"]:
            return None

        signal['prediction'] = direction
        price = signal['price']
        atr = signal.get('atr', 0)

        sr_buffer = atr * 1.5 if atr else price * 0.01
        support = signal.get('support')
        resistance = signal.get('resistance')

        if direction == "LONG":
            if not resistance or resistance - price < sr_buffer:
                return None
        elif direction == "SHORT":
            if not support or price - support < sr_buffer:
                return None

        boost = multi_timeframe_boost(symbol, exchange, direction)
        signal['confidence'] += boost

        signal["tp1_possibility"] = max(70, 100 - abs(signal["tp1"] - price) / price * 100)
        signal["tp2_possibility"] = max(60, 95 - abs(signal["tp2"] - price) / price * 100)
        signal["tp3_possibility"] = max(50, 90 - abs(signal["tp3"] - price) / price * 100)

        signal["confidence"] = min(signal["confidence"], 100)

        return signal
    except Exception as e:
        log(f"❌ Engine error for {symbol}: {e}")
        return None
