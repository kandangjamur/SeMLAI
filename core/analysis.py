import ccxt.async_support as ccxt
from core.indicators import calculate_indicators
from utils.logger import logger

async def get_valid_symbols():
    exchange = ccxt.binance()
    try:
        markets = await exchange.load_markets()
        usdt_pairs = [s for s in markets if s.endswith("/USDT") and markets[s]['active']]
        return usdt_pairs[:100]
    finally:
        await exchange.close()

async def analyze_symbol(symbol: str):
    exchange = ccxt.binance()
    try:
        ohlcv_1h = await exchange.fetch_ohlcv(symbol, timeframe="1h", limit=100)
        ohlcv_15m = await exchange.fetch_ohlcv(symbol, timeframe="15m", limit=100)
        if not ohlcv_1h or not ohlcv_15m:
            return None
        df = await calculate_indicators(symbol, ohlcv_15m, ohlcv_1h)
        if df is None or df.empty:
            return None

        latest = df.iloc[-1]
        direction = latest["direction"]
        confidence = latest["confidence"]
        tp_possibility = latest["tp_possibility"]

        if direction not in ["LONG", "SHORT"]:
            return None

        formatted = (
            f"<b>{symbol}</b>\n"
            f"Direction: <b>{direction}</b>\n"
            f"Confidence: <b>{confidence:.2f}</b>\n"
            f"TP Possibility: <b>{tp_possibility}</b>"
        )

        return {
            "symbol": symbol,
            "direction": direction,
            "confidence": confidence,
            "tp_possibility": tp_possibility,
            "formatted": formatted
        }
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}")
        return None
    finally:
        await exchange.close()
