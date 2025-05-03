import asyncio
from core.indicators import calculate_indicators

TIMEFRAMES = ['15m', '1h', '4h', '1d']

async def fetch_ohlcv(exchange, symbol: str, timeframe: str):
    try:
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, limit=100)
        await asyncio.sleep(0.4)  # Rate limiting
        return ohlcv
    except Exception:
        return None

async def analyze_symbol(symbol: str):
    from utils.exchange import get_exchange  # Delayed import to avoid boot conflict
    exchange = await get_exchange()

    try:
        tasks = [fetch_ohlcv(exchange, symbol, tf) for tf in TIMEFRAMES]
        data_sets = await asyncio.gather(*tasks)
        results = [calculate_indicators(data, tf) for data, tf in zip(data_sets, TIMEFRAMES) if data]

        if not results or len(results) < len(TIMEFRAMES):
            return None

        long_count = sum(1 for r in results if r["signal"] == "LONG")
        short_count = sum(1 for r in results if r["signal"] == "SHORT")

        if long_count == len(TIMEFRAMES):
            direction = "LONG"
        elif short_count == len(TIMEFRAMES):
            direction = "SHORT"
        else:
            return None

        confidence = sum(r["confidence"] for r in results) // len(results)
        tp1_possibility = results[-1].get("tp1_possibility", 0)
        tp_levels = results[-1].get("tp_levels", [])

        return {
            "symbol": symbol,
            "direction": direction,
            "confidence": confidence,
            "tp1_possibility": tp1_possibility,
            "tp_levels": tp_levels
        }

    except Exception:
        return None
    finally:
        if hasattr(exchange, "close"):
            await exchange.close()
