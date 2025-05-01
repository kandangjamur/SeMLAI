import numpy as np
from utils.logger import log, crash_logger

async def predict_trend(symbol, exchange):
    try:
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe="15m", limit=50)
        if len(ohlcv) < 20:
            log(f"⚠️ Insufficient data for trend prediction for {symbol}")
            return None

        closes = np.array([x[4] for x in ohlcv])
        highs = np.array([x[2] for x in ohlcv])
        lows = np.array([x[3] for x in ohlcv])

        # EMA Crossover
        ema12 = calculate_ema(closes, 12)
        ema26 = calculate_ema(closes, 26)
        ema_cross = ema12[-1] > ema26[-1] and ema12[-2] <= ema26[-2]

        # ADX for trend strength
        adx = calculate_adx(highs, lows, closes)
        trend_strength = adx[-1] > 25

        # Order Book Sentiment
        order_book = await exchange.fetch_order_book(symbol, limit=10)
        buy_pressure = sum([x[1] for x in order_book['bids']])
        sell_pressure = sum([x[1] for x in order_book['asks']])
        sentiment = buy_pressure > sell_pressure * 1.2

        # Volatility Check
        atr = calculate_atr(ohlcv)
        if atr < np.mean([calculate_atr(ohlcv[-10:])]) * 0.5:
            log(f"⚠️ Low volatility for {symbol}, no trend")
            return None

        # Trend Decision
        if ema_cross and trend_strength and sentiment and closes[-1] > closes[-2]:
            log(f"✅ LONG trend detected for {symbol}")
            return "LONG"
        elif not ema_cross and trend_strength and not sentiment and closes[-1] < closes[-2]:
            log(f"✅ SHORT trend detected for {symbol}")
            return "SHORT"

        log(f"⚠️ No clear trend for {symbol}")
        return None
    except Exception as e:
        log(f"❌ Error predicting trend for {symbol}: {e}")
        crash_logger.error(f"Error predicting trend for {symbol}: {e}")
        return None

def calculate_ema(prices, period):
    try:
        alpha = 2 / (period + 1)
        ema = [prices[0]]
        for price in prices[1:]:
            ema.append(alpha * price + (1 - alpha) * ema[-1])
        return np.array(ema)
    except:
        return prices

def calculate_adx(highs, lows, closes, period=14):
    try:
        trs = []
        dm_plus = []
        dm_minus = []
        for i in range(1, len(highs)):
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
            trs.append(tr)
            dm_plus.append(max(highs[i] - highs[i-1], 0) if highs[i] - highs[i-1] > lows[i-1] - lows[i] else 0)
            dm_minus.append(max(lows[i-1] - lows[i], 0) if lows[i-1] - lows[i] > highs[i] - highs[i-1] else 0)
        
        tr_smooth = np.mean(trs[-period:]) if len(trs) >= period else 0
        dm_plus_smooth = np.mean(dm_plus[-period:]) if len(dm_plus) >= period else 0
        dm_minus_smooth = np.mean(dm_minus[-period:]) if len(dm_minus) >= period else 0
        
        di_plus = (dm_plus_smooth / tr_smooth) * 100 if tr_smooth != 0 else 0
        di_minus = (dm_minus_smooth / tr_smooth) * 100 if tr_smooth != 0 else 0
        dx = abs(di_plus - di_minus) / (di_plus + di_minus) * 100 if (di_plus + di_minus) != 0 else 0
        return [dx]
    except:
        return [0]

def calculate_atr(ohlcv, period=14):
    try:
        highs = [x[2] for x in ohlcv]
        lows = [x[3] for x in ohlcv]
        closes = [x[4] for x in ohlcv]
        trs = []
        for i in range(1, len(highs)):
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
            trs.append(tr)
        return np.mean(trs[-period:]) if len(trs) >= period else 0.01
    except:
        return 0.01
