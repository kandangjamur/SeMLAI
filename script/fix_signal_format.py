from utils.logger import log
import os
import sys
import pandas as pd
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def fix_signal_format():
    """Fix incorrectly formatted signals in the CSV files"""
    log("Starting signal format fix", level='INFO')

    signals_file = "logs/signals_log_new.csv"
    if not os.path.exists(signals_file):
        log(f"Signal file not found: {signals_file}", level='ERROR')
        return

    try:
        # Read the signals file
        df = pd.read_csv(signals_file)
        log(f"Loaded {len(df)} signals from {signals_file}", level='INFO')

        # Create a backup
        backup_file = f"{signals_file}.backup"
        df.to_csv(backup_file, index=False)
        log(f"Created backup file: {backup_file}", level='INFO')

        # Find malformed signals (where timeframe appears in unexpected column)
        malformed = df[df['tp1'].astype(str).str.contains('m$|h$|d$')]

        if len(malformed) > 0:
            log(f"Found {len(malformed)} malformed signals", level='INFO')

            # Fix each malformed signal
            for idx, row in malformed.iterrows():
                symbol = row['symbol']
                log(f"Fixing signal for {symbol}", level='INFO')

                # Extract correct values from wrong columns
                timeframe = row['tp1']
                direction = row['direction']
                confidence = float(row['confidence'])
                timestamp = row['timestamp']

                # Try to extract price values from various columns
                try:
                    indicators = row['tp2']
                    entry_price = float(row['tp3'].replace(',', ''))
                    sl_offset = float(row['sl'])

                    # Calculate TP/SL levels based on entry and typical ratios
                    if direction == 'LONG':
                        sl = entry_price * (1 - sl_offset/100)
                        tp1 = entry_price * (1 + 1.5/100)
                        tp2 = entry_price * (1 + 3.0/100)
                        tp3 = entry_price * (1 + 5.0/100)
                    else:  # SHORT
                        sl = entry_price * (1 + sl_offset/100)
                        tp1 = entry_price * (1 - 1.5/100)
                        tp2 = entry_price * (1 - 3.0/100)
                        tp3 = entry_price * (1 - 5.0/100)

                    # Create corrected row
                    df.at[idx, 'tp1'] = tp1
                    df.at[idx, 'tp2'] = tp2
                    df.at[idx, 'tp3'] = tp3
                    df.at[idx, 'sl'] = sl
                    df.at[idx, 'entry'] = entry_price
                    df.at[idx, 'timeframe'] = timeframe
                    df.at[idx, 'indicators_used'] = indicators

                    # Make sure tp_possibility fields are correct
                    df.at[idx, 'tp1_possibility'] = 0.7
                    df.at[idx, 'tp2_possibility'] = 0.5
                    df.at[idx, 'tp3_possibility'] = 0.3

                    # Ensure status is pending
                    df.at[idx, 'status'] = 'pending'

                    log(
                        f"Fixed signal for {symbol}: Entry={entry_price}, SL={sl}, TP1={tp1}", level='INFO')

                except Exception as e:
                    log(f"Error fixing signal for {symbol}: {e}",
                        level='ERROR')
                    # Mark as invalid if we can't fix it
                    df.at[idx, 'status'] = 'invalid'

        # Save the fixed file
        df.to_csv(signals_file, index=False)
        log(f"Saved fixed signals to {signals_file}", level='INFO')

        # Now synchronize with performance tracking
        sync_with_performance(df)

    except Exception as e:
        log(f"Error fixing signal format: {e}", level='ERROR')


def sync_with_performance(signals_df):
    """Ensure all signals are properly tracked in performance file"""
    performance_file = "logs/signal_performance.csv"

    # Create performance file if it doesn't exist
    if not os.path.exists(performance_file):
        columns = [
            'symbol', 'direction', 'timeframe', 'confidence', 'success',
            'timestamp', 'entry', 'exit_price', 'tp1', 'tp2', 'tp3', 'sl',
            'status', 'profit_loss', 'hit_time', 'duration_minutes'
        ]
        pd.DataFrame(columns=columns).to_csv(performance_file, index=False)
        log(
            f"Created performance tracking file: {performance_file}", level='INFO')

    try:
        # Load performance data
        perf_df = pd.read_csv(performance_file)
        log(f"Loaded {len(perf_df)} records from performance file", level='INFO')

        # Find signals that aren't in performance tracking
        new_performance_records = []
        sync_count = 0

        for idx, signal in signals_df.iterrows():
            symbol = signal['symbol']
            timestamp = signal['timestamp']

            # Check if this signal exists in performance tracking
            exists = False
            for pidx, perf in perf_df.iterrows():
                if perf['symbol'] == symbol and str(perf['timestamp']) == str(timestamp):
                    exists = True
                    break

            if not exists and signal['status'] != 'invalid':
                # Create performance record
                perf_record = {
                    'symbol': symbol,
                    'direction': signal['direction'],
                    'timeframe': signal.get('timeframe', ''),
                    'confidence': signal['confidence'],
                    'success': '',
                    'timestamp': timestamp,
                    'entry': signal['entry'],
                    'exit_price': signal.get('exit_price', 0),
                    'tp1': signal['tp1'],
                    'tp2': signal['tp2'],
                    'tp3': signal['tp3'],
                    'sl': signal['sl'],
                    'status': signal['status'],
                    'profit_loss': signal.get('profit_loss', 0),
                    'hit_time': '',
                    'duration_minutes': 0
                }
                new_performance_records.append(perf_record)
                sync_count += 1

        # Add new records to performance tracking
        if sync_count > 0:
            perf_df = pd.concat([perf_df, pd.DataFrame(
                new_performance_records)], ignore_index=True)
            perf_df.to_csv(performance_file, index=False)
            log(f"Added {sync_count} signals to performance tracking", level='INFO')
        else:
            log("No new signals to add to performance tracking", level='INFO')

    except Exception as e:
        log(f"Error syncing with performance: {e}", level='ERROR')


if __name__ == "__main__":
    fix_signal_format()
