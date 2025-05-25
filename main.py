import asyncio
import logging
import pandas as pd
import ccxt.async_support as ccxt
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from core.analysis import analyze_symbol_multi_timeframe
from model.predictor import SignalPredictor
from telebot.sender import send_telegram_signal
from datetime import datetime, timedelta
import httpx
from utils.confidence import ConfidenceManager
from utils.performance_tracker import PerformanceTracker
from script.update_signal_status import SignalStatusUpdater
import os
import uvicorn


# Initialize the performance tracker
performance_tracker = PerformanceTracker()

# Initialize the confidence manager
confidence_manager = ConfidenceManager()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("crypto-signal-bot")

# Initialize FastAPI app
app = FastAPI(title="Crypto Sniper Bot")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EXCHANGE = ccxt.binance()
SYMBOL_LIMIT = 150
TIMEFRAMES = ["15m", "1h", "4h", "1d"]
MIN_VOLUME = 3000000
CONFIDENCE_THRESHOLD = 70.0  # Lowered to allow 70% confidence signals
COOLDOWN_PERIOD = 21600  # 6 hours

predictor = SignalPredictor()
log.info("Signal Predictor initialized successfully")

cooldowns = {}
http_client = None


async def update_signal_statuses_task():
    """Background task to periodically update signal statuses"""
    while True:
        try:
            updater = SignalStatusUpdater()
            updater.update_signal_statuses()
        except Exception as e:
            logger.error(f"Error updating signal statuses: {e}")

        # Wait for 15 minutes before next update
        await asyncio.sleep(15 * 60)  # 15 minutes


async def fetch_ohlcv(symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
    for attempt in range(3):  # Retry logic for API limits
        try:
            ohlcv = await EXCHANGE.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(
                ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except ccxt.RateLimitExceeded:
            log.warning(
                f"[{symbol}] Rate limit exceeded for {timeframe}, retrying in 10s")
            await asyncio.sleep(10)
        except Exception as e:
            log.error(
                f"[{symbol}] Error fetching OHLCV for {timeframe}: {str(e)}")
            return pd.DataFrame()
    log.error(
        f"[{symbol}] Failed to fetch OHLCV for {timeframe} after 3 attempts")
    return pd.DataFrame()


async def get_high_volume_symbols() -> List[str]:
    try:
        await EXCHANGE.load_markets()
        tickers = await EXCHANGE.fetch_tickers()
        symbols = [
            symbol for symbol, ticker in tickers.items()
            if symbol.endswith('/USDT') and ticker.get('quoteVolume', 0) >= MIN_VOLUME
        ]
        log.info(
            f"Selected {len(symbols)} USDT pairs with volume >= ${MIN_VOLUME}")
        return symbols[:SYMBOL_LIMIT]
    except Exception as e:
        log.error(f"Error fetching symbols: {str(e)}")
        return []


async def save_signal_to_csv(signal: Dict):
    try:
        # Make a copy of the signal to avoid modifying the original
        signal_copy = signal.copy()

        # Ensure timestamp is properly formatted
        if 'timestamp' in signal_copy:
            if isinstance(signal_copy['timestamp'], pd.Timestamp):
                signal_copy['timestamp'] = signal_copy['timestamp'].strftime(
                    '%Y-%m-%d %H:%M:%S')
            elif isinstance(signal_copy['timestamp'], (int, float)):
                signal_copy['timestamp'] = datetime.fromtimestamp(
                    signal_copy['timestamp'] /
                    1000 if signal_copy['timestamp'] > 1000000000000 else signal_copy['timestamp']
                ).strftime('%Y-%m-%d %H:%M:%S')
            elif signal_copy['timestamp'] == 'timestamp' or not signal_copy['timestamp']:
                signal_copy['timestamp'] = datetime.now().strftime(
                    '%Y-%m-%d %H:%M:%S')
        else:
            signal_copy['timestamp'] = datetime.now().strftime(
                '%Y-%m-%d %H:%M:%S')

        # Add status if not present
        if 'status' not in signal_copy:
            signal_copy['status'] = 'pending'

        # Add timeframe if missing
        if 'timeframe' not in signal_copy and 'tp1' in signal_copy and isinstance(signal_copy['tp1'], str) and len(signal_copy['tp1']) <= 3:
            signal_copy['timeframe'] = signal_copy['tp1']

        # Add missing possibility fields with default values
        if 'tp1_possibility' not in signal_copy:
            signal_copy['tp1_possibility'] = 0.7
        if 'tp2_possibility' not in signal_copy:
            signal_copy['tp2_possibility'] = 0.5
        if 'tp3_possibility' not in signal_copy:
            signal_copy['tp3_possibility'] = 0.3

        # Make sure we have numeric values where required
        numeric_fields = ['entry', 'tp1', 'tp2', 'tp3', 'sl', 'confidence']
        for field in numeric_fields:
            if field in signal_copy and not isinstance(signal_copy[field], (int, float)):
                try:
                    signal_copy[field] = float(
                        str(signal_copy[field]).replace(',', ''))
                except (ValueError, TypeError):
                    log.warning(
                        f"Couldn't convert {field} to number: {signal_copy[field]}")

        # Check if file exists to determine if we need headers
        file_exists = os.path.exists('logs/signals_log_new.csv')

        # Create DataFrame and save to CSV
        df = pd.DataFrame([signal_copy])
        df.to_csv('logs/signals_log_new.csv', mode='a', index=False,
                  header=not file_exists)
        log.info(
            f"Signal logged to logs/signals_log_new.csv with timestamp {signal_copy['timestamp']}")

        # Also add to performance tracking
        try:
            # Create performance record explicitly
            perf_record = {
                'symbol': signal_copy['symbol'],
                'direction': signal_copy['direction'],
                'timeframe': signal_copy.get('timeframe', ''),
                'confidence': signal_copy['confidence'],
                'success': '',
                'timestamp': signal_copy['timestamp'],
                'entry': signal_copy['entry'],
                'exit_price': 0,
                'tp1': signal_copy['tp1'],
                'tp2': signal_copy['tp2'],
                'tp3': signal_copy['tp3'],
                'sl': signal_copy['sl'],
                'status': 'pending',
                'profit_loss': 0,
                'hit_time': '',
                'duration_minutes': 0
            }

            # Check if performance file exists
            perf_file = "logs/signal_performance.csv"
            if not os.path.exists(perf_file):
                pd.DataFrame([perf_record]).to_csv(perf_file, index=False)
                log.info(f"Created performance file with new signal")
            else:
                # Check if signal already exists in performance tracking
                perf_df = pd.read_csv(perf_file)
                exists = False

                for _, perf in perf_df.iterrows():
                    if (perf['symbol'] == signal_copy['symbol'] and
                            str(perf['timestamp']) == str(signal_copy['timestamp'])):
                        exists = True
                        break

                if not exists:
                    # Add new record
                    perf_df = pd.concat(
                        [perf_df, pd.DataFrame([perf_record])], ignore_index=True)
                    perf_df.to_csv(perf_file, index=False)
                    log.info(f"Added signal to performance tracking")
                else:
                    log.info(f"Signal already exists in performance tracking")

        except Exception as e:
            log.error(f"Error updating performance tracking: {str(e)}")

    except Exception as e:
        log.error(f"Error saving signal to CSV: {str(e)}")


async def process_symbol(symbol: str):
    log.info(f"[{symbol}] Checking for cooldown")

    if symbol in cooldowns:
        cooldown_end = cooldowns[symbol] + timedelta(seconds=COOLDOWN_PERIOD)
        if datetime.utcnow() < cooldown_end:
            log.info(
                f"[{symbol}] In cooldown until {cooldown_end} across all timeframes")
            return

    log.info(f"[{symbol}] Starting multi-timeframe analysis")

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

    result = await analyze_symbol_multi_timeframe(EXCHANGE, symbol, TIMEFRAMES, predictor)

    if result and 'signals' in result and result['signals']:
        best_signal = max(result['signals'],
                          key=lambda x: x['confidence'], default=None)
        if best_signal and best_signal['confidence'] >= CONFIDENCE_THRESHOLD:
            cooldowns[symbol] = datetime.utcnow()
            log.info(
                f"[{symbol}] Added to cooldown for {COOLDOWN_PERIOD/3600} hours across all timeframes")

            # Add trade type
            best_signal['trade_type'] = "Normal" if best_signal['confidence'] >= 80 else "Scalping"

            # Keep timestamp as 2025 as this seems to be your current year setting
            current_time = datetime.now()
            best_signal['timestamp'] = current_time.strftime(
                '%Y-%m-%d %H:%M:%S')

            # Ensure all required fields exist
            required_fields = ['tp1_possibility',
                               'tp2_possibility', 'tp3_possibility', 'timeframe']
            for field in required_fields:
                if field not in best_signal:
                    if 'possibility' in field:
                        best_signal[field] = 0.7 if 'tp1' in field else 0.5 if 'tp2' in field else 0.3
                    elif field == 'timeframe':
                        best_signal[field] = next(iter(timeframe_data.keys()))

            # Send signal to Telegram only if confidence is high enough
            telegram_sent = False
            try:
                telegram_sent = await send_telegram_signal(symbol, best_signal)
                if telegram_sent:
                    log.info(
                        f"[{best_signal['symbol']}] HIGH CONFIDENCE ({best_signal['confidence']:.2f}%) Telegram signal sent successfully")
                else:
                    log.info(
                        f"[{best_signal['symbol']}] Signal recorded but not sent to Telegram (confidence below 90%)")
            except Exception as e:
                log.error(f"Error sending Telegram signal: {str(e)}")

            # Always save the signal to CSV regardless of Telegram status
            await save_signal_to_csv(best_signal)

            if telegram_sent:
                log.info(f"✅ HIGH CONFIDENCE Signal SENT to Telegram ✅")
            else:
                log.info(f"📊 Signal recorded but not sent to Telegram")

        else:
            log.info(f"⚠️ {symbol} - No signal with sufficient confidence")
    else:
        log.info(f"⚠️ {symbol} - No valid signals")


async def process_signals(symbol, timeframe, signal_data, threshold=60.0):
    # Load telegram minimum confidence
    telegram_min = 95.0  # Default
    config_path = os.path.join("config", "confidence_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                telegram_min = config.get("telegram_minimum", 95.0)
        except Exception as e:
            logger.error(f"Error loading confidence config: {str(e)}")

    # Your existing signal processing code...

    # When sending to Telegram:
    if signal["confidence"] >= telegram_min:
        logger.info(
            f"[{symbol}] HIGH CONFIDENCE SIGNAL: {signal['direction']} "
            f"with {signal['confidence']:.2f}% confidence - Sending to Telegram"
        )
        # Send telegram alert
        if TELEGRAM_ENABLED:
            await sender.send_telegram_signal(symbol, signal)
    else:
        # Signal is valid but below Telegram threshold
        logger.info(
            f"[{symbol}] Valid signal with {signal['confidence']:.2f}% confidence "
            f"(below {telegram_min}% Telegram threshold)"
        )

    # Always save to CSV regardless of confidence
    await save_signal_to_csv(signal)


async def scan_symbols():
    global http_client
    if http_client is None:
        http_client = httpx.AsyncClient()
    log.info(f"Scanning {SYMBOL_LIMIT} symbols across {TIMEFRAMES}")
    symbols = await get_high_volume_symbols()

    for symbol in symbols:
        try:
            await process_symbol(symbol)
            await asyncio.sleep(30)  # Increased to 30s to avoid API limits
        except Exception as e:
            log.error(f"Error processing {symbol}: {str(e)}")
    await asyncio.sleep(1800)  # Increased to 30 minutes


@app.on_event("startup")
async def startup_event():
    log.info("Starting bot...")
    try:
        await EXCHANGE.load_markets()
        log.info("Binance API connection successful")

        # Start background tasks
        asyncio.create_task(check_signal_status())
        asyncio.create_task(update_signal_statuses_task())

        while True:
            try:
                await scan_symbols()
                log.info("Scan complete, waiting for next cycle...")
                await asyncio.sleep(1800)  # Increased to 30 minutes
            except Exception as e:
                log.error(f"Error in scan cycle: {str(e)}")
                await asyncio.sleep(1800)
    except Exception as e:
        log.error(f"Error in startup: {str(e)}")
        await asyncio.sleep(1800)


@app.on_event("shutdown")
async def shutdown_event():
    log.info("Shutting down")
    try:
        await EXCHANGE.close()
        log.info("Binance connection closed successfully")
        if http_client:
            await http_client.aclose()
            log.info("HTTPX client closed successfully")
    except Exception as e:
        log.error(f"Error closing resources: {str(e)}")


@app.get("/health")
async def health_check():
    try:
        if EXCHANGE is None or not hasattr(EXCHANGE, 'markets'):
            log.error(
                "Health check failed: Exchange not initialized or markets not loaded")
            return {"status": "unhealthy", "error": "Exchange not initialized or markets not loaded"}, 500
        log.info("Health check passed")
        return {"status": "healthy", "timestamp": str(datetime.utcnow())}
    except Exception as e:
        log.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}, 500


async def check_and_fix_signal_logs():
    """Check signal logs for timestamp issues and fix them"""
    log.info("Checking signal logs for timestamp issues...")

    for logfile in ['logs/signals_log.csv', 'logs/signals_log_new.csv']:
        if os.path.exists(logfile):
            try:
                df = pd.read_csv(logfile)
                if 'timestamp' in df.columns:
                    # Check for literal "timestamp" values
                    timestamp_issues = (df['timestamp'] == 'timestamp').sum()
                    if timestamp_issues > 0:
                        log.warning(
                            f"Found {timestamp_issues} rows with literal 'timestamp' value in {logfile}")
                        # Replace with current time
                        df.loc[df['timestamp'] == 'timestamp', 'timestamp'] = datetime.now().strftime(
                            '%Y-%m-%d %H:%M:%S')

                    # Save fixed file
                    df.to_csv(logfile, index=False)
                    log.info(f"Fixed {logfile} timestamp issues")
            except Exception as e:
                log.error(f"Error checking {logfile}: {str(e)}")

    log.info("Signal log check complete")


async def check_signal_status():
    """Background task to periodically check and update signal statuses"""
    while True:
        try:
            log.info("Running signal status check...")

            # Load files
            signals_file = "logs/signals_log_new.csv"
            if not os.path.exists(signals_file):
                log.warning("Signals file not found")
                await asyncio.sleep(3600)  # Wait and retry later
                continue

            try:
                # Update to use the current pandas parameter
                df = pd.read_csv(signals_file, on_bad_lines='skip')

                # Check for column issues
                if 'status' not in df.columns:
                    df['status'] = 'pending'
                    log.info("Added missing 'status' column")

                # Save the fixed CSV
                df.to_csv(signals_file, index=False)

                # Filter for pending signals
                pending_signals = df[df['status'] == 'pending']
            except Exception as e:
                log.error(f"Error loading signal file: {str(e)}")

                # Try to fix the CSV file manually
                try:
                    with open(signals_file, 'r') as f:
                        lines = f.readlines()

                    # Get header line
                    header = lines[0].strip()
                    headers = header.split(',')
                    num_columns = len(headers)

                    # Fix other lines
                    fixed_lines = [header]
                    for i, line in enumerate(lines[1:], 1):
                        cols = line.strip().split(',')
                        if len(cols) > num_columns:
                            # Too many columns - combine some values
                            fixed_line = ','.join(
                                cols[:num_columns-1]) + ',"' + ','.join(cols[num_columns-1:]) + '"'
                        elif len(cols) < num_columns:
                            # Too few columns - add empty values
                            fixed_line = line.strip() + ',' * (num_columns - len(cols) - 1)
                        else:
                            fixed_line = line.strip()
                        fixed_lines.append(fixed_line)

                    # Write fixed file
                    with open(signals_file + '.fixed', 'w') as f:
                        f.write('\n'.join(fixed_lines))

                    # Try to load the fixed file
                    df = pd.read_csv(signals_file + '.fixed',
                                     on_bad_lines='skip')
                    df.to_csv(signals_file, index=False)
                    log.info("Fixed CSV file format issues")

                    # Filter for pending signals
                    pending_signals = df[df['status'] == 'pending']
                except Exception as fix_error:
                    log.error(f"Failed to fix CSV file: {str(fix_error)}")
                    await asyncio.sleep(3600)  # Wait and retry later
                    continue

            if len(pending_signals) == 0:
                log.info("No pending signals to check")
                await asyncio.sleep(3600)  # Check again in an hour
                continue

            log.info(f"Checking {len(pending_signals)} pending signals")

            # Create non-async exchange instance for price checks
            exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })

            # Check each signal
            updates = 0
            for idx, signal in pending_signals.iterrows():
                symbol = signal['symbol']
                direction = signal['direction']

                try:
                    entry = float(signal['entry'])
                    tp1 = float(signal['tp1'])
                    tp2 = float(signal['tp2'])
                    tp3 = float(signal['tp3'])
                    sl = float(signal['sl'])

                    # Get current price - NOTE: Using synchronous version
                    ticker = exchange.fetch_ticker(symbol)
                    current_price = ticker['last']

                    # Check for TP/SL hits
                    status = None
                    profit_loss = 0
                    success = "NO"

                    if direction == "LONG":
                        if current_price <= sl:
                            status = "sl"
                            profit_loss = (current_price - entry) / entry * 100
                        elif current_price >= tp3:
                            status = "tp3"
                            profit_loss = (current_price - entry) / entry * 100
                            success = "YES"
                        elif current_price >= tp2:
                            status = "tp2"
                            profit_loss = (current_price - entry) / entry * 100
                            success = "YES"
                        elif current_price >= tp1:
                            status = "tp1"
                            profit_loss = (current_price - entry) / entry * 100
                            success = "YES"
                    elif direction == "SHORT":
                        if current_price >= sl:
                            status = "sl"
                            profit_loss = (entry - current_price) / entry * 100
                        elif current_price <= tp3:
                            status = "tp3"
                            profit_loss = (entry - current_price) / entry * 100
                            success = "YES"
                        elif current_price <= tp2:
                            status = "tp2"
                            profit_loss = (entry - current_price) / entry * 100
                            success = "YES"
                        elif current_price <= tp1:
                            status = "tp1"
                            profit_loss = (entry - current_price) / entry * 100
                            success = "YES"

                    if status:
                        # Update signal in CSV
                        df.at[idx, 'status'] = status
                        df.at[idx, 'exit_price'] = current_price
                        df.at[idx, 'profit_loss'] = round(profit_loss, 2)
                        updates += 1

                        # Update performance tracking
                        try:
                            performance_tracker.update_signal_status(
                                symbol,
                                signal['timestamp'],
                                status,
                                exit_price=current_price,
                                profit_loss=profit_loss,
                                success=success
                            )
                            log.info(
                                f"Updated {symbol} signal to {status}, P/L: {profit_loss:.2f}%")
                        except Exception as e:
                            log.error(f"Error updating performance: {str(e)}")

                    # Rate limit
                    await asyncio.sleep(0.1)

                except Exception as e:
                    log.error(f"Error checking {symbol}: {str(e)}")

            # Save updated signals
            if updates > 0:
                df.to_csv(signals_file, index=False)
                log.info(f"Updated {updates} signals")

            await asyncio.sleep(3600)  # Check every hour

        except Exception as e:
            log.error(f"Error in signal status check: {str(e)}")
            await asyncio.sleep(3600)  # Retry in an hour


async def main():

    # First check and fix signal logs
    await check_and_fix_signal_logs()

    # Sync existing signals to performance tracking
    performance_tracker.sync_pending_signals()

if __name__ == "__main__":
    logging.info("Starting Crypto Sniper Bot...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload during development
        workers=1,
        timeout_keep_alive=240
    )