import numpy as np
from core.indicators import calculate_indicators
from utils.logger import log, crash_logger

TIMEFRAMES = ["15m", "1h", "4h", "1d"]

async def multi_timeframe_analysis(symbol, exchange):
    try:
        timeframe_results = []
        ohlcv_data = {}

        for tf in TIMEFRAMES:
            try:
                ohlcv = await exchange.fetch_ohlcv(symbol, timeframe=tf, limit=100)
                if not ohlcv or len(ohlcv) < 50:
                    log(f"⚠️ Insufficient data for {symbol} on {tf}: {len(ohlcv)} candles")
                    continue

                ohlcv_data[tf] = ohlcv
                signal = calculate_indicators(symbol, ohlcv)
                if signal and not np.isnan(signal.get('confidence', 0)) and not np.isnan(signal.get('price', 0)):
                    signal["timeframe"] = tf
                    # Calculate VWAP
                    vwap = calculate_vwap(ohlcv)
                    signal["vwap"] = vwap
                    # Calculate ATR for dynamic TP/SL
                    atr = calculate_atr(ohlcv)
                    signal["atr"] = atr
                    # RSI Divergence
                    closes = [x[4] for x in ohlcv]
                    rsi = calculate_rsi(closes)
                    rsi_divergence = calculate_rsi_divergence(closes, rsi)
                    if rsi_divergence:
                        signal["confidence"] += 15  # Boost confidence for divergence
                    timeframe_results.append(signal)
                else:
                    log(f"⚠️ Invalid signal for {symbol} on {tf}")
            except Exception as e:
                log(f"❌ Error in {symbol} on {tf}: {e}")
                crash_logger.error(f"Error in {symbol} on {tf}: {e}")
                continue

        # Volatility Filter: Skip if ATR is too low
        atr_values = [s["atr"] for s in timeframe_results if "atr" in s]
        if atr_values and np.mean(atr_values) < np.mean(atr_values[-10:]) * 0.5:
            log(f"⚠️ Low volatility for {symbol}, skipping")
            return None

        strong = [s for s in timeframe_results if s['confidence'] >= 50]

        # Relaxed requirement: 2+ timeframes if confidence > 60
        if len(strong) >= 3 or (len(strong) >= 2 and any(s['confidence'] > 60 for s in strong)):
            prices = [s["price"] for s in strong]
            types = set([s["trade_type"] for s in strong])
            avg_conf = np.mean([s["confidence"] for s in strong])

            if max(prices) - min(prices) > min(prices) * 0.02:
                log(f"⚠️ Price deviation too high for {symbol} across timeframes")
                return None

            if len(types) > 1:
                log(f"⚠️ Inconsistent trade types for {symbol}: {types}")
                return None

            best_signal = max(strong, key=lambda s: s["confidence"])
            # Adjust TP/SL based on ATR
            atr = best_signal.get("atr", 0.01)
            if best_signal["direction"] == "LONG":
                best_signal["tp1"] = best_signal["price"] + atr * 1.2
                best_signal["tp2"] = best_signal["price"] + atr * 2.0
                best_signal["tp3"] = best_signal["price"] + atr * 3.0
                best_signal["sl"] = best_signal["price"] - atr * 0.8
            else:  # SHORT
                best_signal["tp1"] = best_signal["price"] - atr * 1.2
                best_signal["tp2"] = best_signal["price"] - atr * 2.0
                best_signal["tp3"] = best_signal["price"] - atr * 3.0
                best_signal["sl"] = best_signal["price"] + atr * 0.8

            best_signal["confidence"] = round(min(avg_conf, 100), 2)
            log(f"✅ Strong multi-timeframe signal for {symbol} with avg confidence {avg_conf}")
            return best_signal

        log(f"⚠️ No consistent strong signals for {symbol}")
        return None
    except Exception as e:
        log(f"❌ Error in multi_timeframe_analysis for {symbol}: {e}")
        crash_logger.error(f"Error in multi_timeframe_analysis for {symbol}: {e}")
        return None

def calculate_vwap(ohlcv):
    try:
        closes = np.array([x[4] for x in ohlcv])
        volumes = np.array([x[5] for x in ohlcv])
        return np.sum(closes * volumes) / np.sum(volumes) if np.sum(volumes) > 0 else closes[-1]
    except:
        return closes[-1]

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

def calculate_rsi(prices, period=14):
    try:
        deltas = np.diff(prices)
        gains = deltas * (deltas > 0)
        losses = -deltas * (deltas < 0)
        avg_gain = np.mean(gains[-period:]) if len(gains) >= period else 0
        avg_loss = np.mean(losses[-period:]) if len(losses) >= period else 0
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        return 100 - (100 / (1 + rs))
    except:
        return 50

def calculate_rsi_divergence(prices, rsi):
    try:
        if len(prices) < 3 or len(rsi) < 3:
            return False
        price_diff = prices[-1] - prices[-2]
        rsi_diff = rsi[-1] - rsi[-2]
        return (price_diff > 0 and rsi_diff < 0) or (price_diff < 0 and rsi_diff > 0)
    except:
        return False
