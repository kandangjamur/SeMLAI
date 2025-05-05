import asyncio
import pandas as pd
from core.analysis import analyze_symbol
from model.predictor import predict_confidence
from core.news_sentiment import fetch_sentiment, adjust_confidence
from utils.logger import log
import ccxt.async_support as ccxt
import cachetools

signal_cache = cachetools.TTLCache(maxsize=100, ttl=300)  # 5-minute cache

async def process_symbol(exchange, symbol):
    try:
        if symbol in signal_cache:
            log(f"[{symbol}] Using cached signal")
            return signal_cache[symbol]

        # Rule-based analysis
        signal = await analyze_symbol(exchange, symbol)
        if not signal or signal["confidence"] < 80:
            log(f"[{symbol}] No valid rule-based signal")
            return None

        # ML-based confidence
        df = await exchange.fetch_ohlcv(symbol, "15m", limit=100)
        df = pd.DataFrame(df, columns=["timestamp", "open", "high", "low", "close", "volume"])
        ml_confidence = predict_confidence(symbol, df)
        signal["confidence"] = min(95, (signal["confidence"] + ml_confidence) / 2)

        # Sentiment adjustment
        sentiment_score = await fetch_sentiment(symbol)
        signal["confidence"] = adjust_confidence(symbol, signal["confidence"], sentiment_score)

        if signal["confidence"] < 80 or signal["tp1_chance"] < 75:
            log(f"[{symbol}] Signal filtered: Low confidence or TP1 chance")
            return None

        signal_cache[symbol] = signal
        log(f"[{symbol}] Final signal: {signal['direction']}, Confidence: {signal['confidence']}%")
        return signal
    except Exception as e:
        log(f"[{symbol}] Error in process_symbol: {e}", level='ERROR')
        return None

async def run_engine():
    exchange = ccxt.binance({"enableRateLimit": True})
    try:
        markets = await exchange.load_markets()
        symbols = [s for s in markets.keys() if s.endswith("/USDT") and markets[s].get("active", False)]
        for symbol in symbols[:50]:  # Limit to 50 symbols
            signal = await process_symbol(exchange, symbol)
            if signal:
                log(f"[{symbol}] Signal generated: {signal}")
            await asyncio.sleep(0.5)
    except Exception as e:
        log(f"Error in run_engine: {e}", level='ERROR')
    finally:
        await exchange.close()
