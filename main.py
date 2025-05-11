import asyncio
import logging
import pandas as pd
import ccxt.async_support as ccxt
from fastapi import FastAPI
from typing import List, Dict
from core.analysis import analyze_symbol_multi_timeframe
from predictors.random_forest import RandomForestPredictor
from utils.notifications import send_telegram_message
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("crypto-signal-bot")

# FastAPI app
app = FastAPI()

# Configuration
EXCHANGE = ccxt.binance()
SYMBOL_LIMIT = 150
TIMEFRAMES = ["15m", "1h", "4h", "1d"]
MIN_VOLUME = 1000000  # Minimum 24h volume in USD
CONFIDENCE_THRESHOLD = 60.0  # For combined signal

# Initialize predictor
predictor = RandomForestPredictor()
log.info("Random Forest model loaded successfully")

async def fetch_ohlcv(symbol: str, timeframe: str, limit: int = 50) -> pd.DataFrame:
    try:
        ohlcv = await EXCHANGE.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        log.error(f"[{symbol}] Error fetching OHLCV for {timeframe}: {str(e)}")
        return pd.DataFrame()

async def get_high_volume_symbols() -> List[str]:
    try:
        await EXCHANGE.load_markets()
        tickers = await EXCHANGE.fetch_tickers()
        symbols = [
            symbol for symbol, ticker in tickers.items()
            if symbol.endswith('/USDT') and ticker.get('quoteVolume', 0) >= MIN_VOLUME
        ]
        log.info(f"Selected {len(symbols)} USDT pairs with volume >= ${MIN_VOLUME}")
        return symbols[:SYMBOL_LIMIT]
    except Exception as e:
        log.error(f"Error fetching symbols: {str(e)}")
        return []

async def save_signal_to_csv(signal: Dict):
    try:
        df = pd.DataFrame([signal])
        df.to_csv('logs/signals_log_new.csv', mode='a', index=False, header=not pd.io.common.file_exists('logs/signals_log_new.csv'))
        log.info("Signal logged to logs/signals_log_new.csv")
    except Exception as e:
        log.error(f"Error saving signal to CSV: {str(e)}")

async def process_symbol(symbol: str):
    log.info(f"[{symbol}] Starting multi-timeframe analysis")
    
    # Fetch data for all timeframes
    timeframe_data = {}
    for timeframe in TIMEFRAMES:
        df = await fetch_ohlcv(symbol, timeframe)
        if not df.empty:
            timeframe_data[timeframe] = df
        else:
            log.warning(f"[{symbol}] No OHLCV data for {timeframe}")
    
    if not timeframe_data:
        log.warning(f"[{symbol}] No data available for any timeframe")
        return
    
    # Analyze across all timeframes
    signal = await analyze_symbol_multi_timeframe(symbol, timeframe_data, predictor)
    
    if signal:
        message = (
            f"🔍 {signal['symbol']} | Confidence: {signal['confidence']:.2f} | "
            f"Direction: {signal['direction']} | TP1 Chance: {signal['tp1_possibility']:.2f}"
        )
        await send_telegram_message(message)
        log.info(f"[{signal['symbol']}] Telegram message sent successfully")
        await save_signal_to_csv(signal)
        log.info(f"✅ Signal SENT ✅")
    else:
        log.info(f"⚠️ {symbol} - No valid signal")

async def scan_symbols():
    log.info(f"Scanning {SYMBOL_LIMIT} symbols across {TIMEFRAMES}")
    symbols = await get_high_volume_symbols()
    
    for symbol in symbols:
        await process_symbol(symbol)
        await asyncio.sleep(0.5)  # Prevent API rate limit issues
    await asyncio.sleep(60)  # Wait before next scan

@app.on_event("startup")
async def startup_event():
    log.info("Starting bot...")
    try:
        await EXCHANGE.load_markets()
        log.info("Binance API connection successful")
        while True:
            await scan_symbols()
            log.info("Scan complete, waiting for next cycle...")
            await asyncio.sleep(60)  # Run every minute
    except Exception as e:
        log.error(f"Error in startup: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    log.info("Shutting down")
    await EXCHANGE.close()
    log.info("Binance connection closed successfully")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
