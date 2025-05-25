from utils.logger import log
import os
import sys
import pandas as pd
import ccxt
import asyncio
from datetime import datetime
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def update_pending_signals():
    """Update status of pending signals based on current prices"""
    log("Starting pending signal update process", level='INFO')

    # Load signal performance file
    performance_file = "logs/signal_performance.csv"
    if not os.path.exists(performance_file):
        log("Performance file not found", level='ERROR')
        return

    # Initialize exchange - using non-async version to avoid errors
    try:
        # Create a regular (non-async) ccxt instance
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot'
            }
        })
        exchange.load_markets()
        log("Connected to exchange", level='INFO')
    except Exception as e:
        log(f"Failed to connect to exchange: {e}", level='ERROR')
        return

    # Load performance data
    try:
        df = pd.read_csv(performance_file)
        pending_signals = df[df['status'] == 'pending']

        log(f"Found {len(pending_signals)} pending signals to check", level='INFO')

        # Process each pending signal
        processed_count = 0
        tp_count = 0
        sl_count = 0
        expired_count = 0

        for idx, signal in pending_signals.iterrows():
            symbol = signal['symbol']
            direction = signal['direction']

            # Skip symbols with format issues
            if not isinstance(symbol, str) or not '/' in symbol:
                continue

            try:
                entry = float(signal['entry'])
                tp1 = float(signal['tp1'])
                tp2 = float(signal['tp2'])
                tp3 = float(signal['tp3'])
                sl = float(signal['sl'])
                timestamp = signal['timestamp']
            except (ValueError, KeyError):
                log(f"Invalid signal data for {symbol}", level='WARNING')
                continue

            # Skip if entry is 0 (invalid signal)
            if entry == 0:
                continue

            # Calculate signal age in days
            try:
                signal_time = datetime.strptime(
                    str(timestamp).split('.')[0], '%Y-%m-%d %H:%M:%S')
                age_days = (datetime.now() -
                            signal_time).total_seconds() / (24 * 3600)

                # Expire signals older than 7 days
                if age_days > 7:
                    df.at[idx, 'status'] = "expired"
                    df.at[idx, 'success'] = "NO"
                    df.at[idx, 'hit_time'] = datetime.now().strftime(
                        '%Y-%m-%d %H:%M:%S')
                    expired_count += 1
                    processed_count += 1
                    continue
            except Exception as e:
                log(
                    f"Error calculating signal age for {symbol}: {e}", level='WARNING')

            # Get current price
            try:
                ticker = exchange.fetch_ticker(symbol)
                current_price = ticker['last']

                # Check if TP or SL was hit
                status = None
                profit_loss = 0
                success = "NO"

                if direction == "LONG":
                    if current_price <= sl:
                        status = "sl"
                        profit_loss = (current_price - entry) / entry * 100
                        sl_count += 1
                    elif current_price >= tp3:
                        status = "tp3"
                        profit_loss = (current_price - entry) / entry * 100
                        success = "YES"
                        tp_count += 1
                    elif current_price >= tp2:
                        status = "tp2"
                        profit_loss = (current_price - entry) / entry * 100
                        success = "YES"
                        tp_count += 1
                    elif current_price >= tp1:
                        status = "tp1"
                        profit_loss = (current_price - entry) / entry * 100
                        success = "YES"
                        tp_count += 1
                elif direction == "SHORT":
                    if current_price >= sl:
                        status = "sl"
                        profit_loss = (entry - current_price) / entry * 100
                        sl_count += 1
                    elif current_price <= tp3:
                        status = "tp3"
                        profit_loss = (entry - current_price) / entry * 100
                        success = "YES"
                        tp_count += 1
                    elif current_price <= tp2:
                        status = "tp2"
                        profit_loss = (entry - current_price) / entry * 100
                        success = "YES"
                        tp_count += 1
                    elif current_price <= tp1:
                        status = "tp1"
                        profit_loss = (entry - current_price) / entry * 100
                        success = "YES"
                        tp_count += 1

                if status:
                    # Update dataframe
                    df.at[idx, 'status'] = status
                    df.at[idx, 'exit_price'] = current_price
                    df.at[idx, 'profit_loss'] = round(profit_loss, 2)
                    df.at[idx, 'success'] = success
                    df.at[idx, 'hit_time'] = datetime.now().strftime(
                        '%Y-%m-%d %H:%M:%S')

                    # Calculate duration in minutes
                    try:
                        signal_time = datetime.strptime(
                            str(timestamp).split('.')[0], '%Y-%m-%d %H:%M:%S')
                        duration = (datetime.now() -
                                    signal_time).total_seconds() / 60
                        df.at[idx, 'duration_minutes'] = int(duration)
                    except Exception as e:
                        log(
                            f"Error calculating duration for {symbol}: {e}", level='WARNING')

                    log(f"Updated {symbol} signal to {status}, profit/loss: {profit_loss:.2f}%")
                    processed_count += 1

                # Rate limit compliance
                time.sleep(0.2)

            except Exception as e:
                log(f"Error processing {symbol}: {e}", level='ERROR')

        # Save updated dataframe if we made changes
        if processed_count > 0:
            df.to_csv(performance_file, index=False)

        log(f"Processed {processed_count} signals: {tp_count} TP hits, {sl_count} SL hits, {expired_count} expired", level='INFO')

        # Also update signals_log.csv and signals_log_new.csv with the latest status
        await update_signals_log(df)

    except Exception as e:
        log(f"Error updating pending signals: {e}", level='ERROR')

    log("Signal update process complete", level='INFO')


async def update_signals_log(perf_df):
    """Update status in signals log files based on performance data"""
    log_files = ["logs/signals_log.csv", "logs/signals_log_new.csv"]

    for log_file in log_files:
        if not os.path.exists(log_file):
            continue

        try:
            df = pd.read_csv(log_file)
            updates = 0

            if 'symbol' in df.columns and 'timestamp' in df.columns:
                # Add status column if it doesn't exist
                if 'status' not in df.columns:
                    df['status'] = 'pending'

                # Add exit_price and profit_loss columns if they don't exist
                if 'exit_price' not in df.columns:
                    df['exit_price'] = 0.0
                if 'profit_loss' not in df.columns:
                    df['profit_loss'] = 0.0

                # Update signals based on performance data
                for idx, row in df.iterrows():
                    symbol = row['symbol']
                    timestamp = row['timestamp']

                    # Find matching record in performance data
                    matches = perf_df[(perf_df['symbol'] == symbol) &
                                      (perf_df['timestamp'].astype(str) == str(timestamp))]

                    if not matches.empty:
                        match = matches.iloc[0]
                        if match['status'] != 'pending':
                            df.at[idx, 'status'] = match['status']
                            df.at[idx, 'exit_price'] = match['exit_price']
                            df.at[idx, 'profit_loss'] = match['profit_loss']
                            updates += 1

                if updates > 0:
                    df.to_csv(log_file, index=False)
                    log(f"Updated {updates} signals in {log_file}",
                        level='INFO')

        except Exception as e:
            log(f"Error updating {log_file}: {e}", level='ERROR')

# Run the async function
if __name__ == "__main__":
    asyncio.run(update_pending_signals())
