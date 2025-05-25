from utils.logger import log
import os
import sys
import pandas as pd
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def backfill_performance():
    """Process signal logs and update performance data"""
    signals_log = "logs/signals_log.csv"
    signals_log_new = "logs/signals_log_new.csv"
    performance_log = "logs/signal_performance.csv"

    log("Starting performance data backfill...", level='INFO')

    # Check if files exist
    if not os.path.exists(signals_log) and not os.path.exists(signals_log_new):
        log("No signal log files found. Nothing to backfill.", level='WARNING')
        return

    # Initialize performance log if it doesn't exist
    if not os.path.exists(performance_log):
        columns = [
            'symbol', 'direction', 'timeframe', 'confidence', 'success',
            'timestamp', 'entry', 'exit_price', 'tp1', 'tp2', 'tp3', 'sl',
            'status', 'profit_loss', 'hit_time', 'duration_minutes'
        ]
        pd.DataFrame(columns=columns).to_csv(performance_log, index=False)
        log("Created new performance tracking file", level='INFO')

    # Load performance data
    try:
        perf_df = pd.read_csv(performance_log)
        original_count = len(perf_df)
        log(f"Loaded {original_count} existing performance records", level='INFO')
    except Exception as e:
        log(f"Error loading performance data: {e}", level='ERROR')
        return

    # Process signals_log.csv
    if os.path.exists(signals_log):
        try:
            signals_df = pd.read_csv(signals_log)
            log(f"Processing {len(signals_df)} signals from signals_log.csv", level='INFO')

            # Add status column if it doesn't exist
            if 'status' not in signals_df.columns:
                signals_df['status'] = 'pending'

            # Add needed columns if they don't exist
            for col in ['exit_price', 'profit_loss']:
                if col not in signals_df.columns:
                    signals_df[col] = 0.0

            # Process each signal
            for idx, signal in signals_df.iterrows():
                symbol = signal.get('symbol', '')
                timestamp = signal.get('timestamp', '')

                # Skip if already in performance log with a non-pending status
                existing = perf_df[(perf_df['symbol'] == symbol) &
                                   (perf_df['timestamp'] == timestamp)]

                if len(existing) > 0 and existing['status'].iloc[0] != 'pending':
                    continue

                # Calculate success
                success = ''
                status = signal.get('status', 'pending')
                if status in ['tp1', 'tp2', 'tp3']:
                    success = 'YES'
                elif status == 'sl':
                    success = 'NO'

                # Calculate profit/loss
                profit_loss = 0.0
                if status != 'pending' and 'exit_price' in signal and 'entry' in signal:
                    try:
                        exit_price = float(signal['exit_price'])
                        entry = float(signal['entry'])
                        if entry > 0 and exit_price > 0:
                            if signal['direction'] == 'LONG':
                                profit_loss = (
                                    exit_price - entry) / entry * 100
                            else:  # SHORT
                                profit_loss = (
                                    entry - exit_price) / entry * 100
                    except:
                        pass

                # Calculate duration
                hit_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                duration_minutes = 0
                try:
                    # Fix future timestamp issue
                    if isinstance(timestamp, str) and timestamp.startswith('2025-'):
                        # If timestamp is in 2025, it's likely incorrect - extract just time part
                        time_part = timestamp.split(' ')[1]
                        # Create a new timestamp with today's date
                        timestamp = datetime.now().strftime('%Y-%m-%d') + ' ' + time_part

                    signal_time = datetime.strptime(
                        timestamp, '%Y-%m-%d %H:%M:%S')
                    duration = datetime.now() - signal_time
                    duration_minutes = int(duration.total_seconds() / 60)
                except:
                    pass

                # Create or update record
                if len(existing) == 0:
                    # New record
                    new_record = {
                        'symbol': symbol,
                        'direction': signal.get('direction', ''),
                        'timeframe': signal.get('timeframe', ''),
                        'confidence': signal.get('confidence', 0),
                        'success': success,
                        'timestamp': timestamp,
                        'entry': signal.get('entry', 0),
                        'exit_price': signal.get('exit_price', 0),
                        'tp1': signal.get('tp1', 0),
                        'tp2': signal.get('tp2', 0),
                        'tp3': signal.get('tp3', 0),
                        'sl': signal.get('sl', 0),
                        'status': status,
                        'profit_loss': round(profit_loss, 2),
                        'hit_time': hit_time,
                        'duration_minutes': duration_minutes
                    }
                    perf_df = pd.concat(
                        [perf_df, pd.DataFrame([new_record])], ignore_index=True)
                else:
                    # Update existing record
                    idx = existing.index[0]
                    perf_df.at[idx, 'status'] = status
                    perf_df.at[idx, 'success'] = success
                    perf_df.at[idx, 'hit_time'] = hit_time
                    perf_df.at[idx, 'duration_minutes'] = duration_minutes
                    perf_df.at[idx, 'exit_price'] = signal.get('exit_price', 0)
                    perf_df.at[idx, 'profit_loss'] = round(profit_loss, 2)

                    # Update other fields to ensure consistency
                    for field in ['direction', 'timeframe', 'confidence', 'entry', 'tp1', 'tp2', 'tp3', 'sl']:
                        if field in signal:
                            perf_df.at[idx, field] = signal[field]
        except Exception as e:
            log(f"Error processing signals_log.csv: {e}", level='ERROR')

    # Process signals_log_new.csv similarly
    if os.path.exists(signals_log_new):
        try:
            signals_df = pd.read_csv(signals_log_new)
            log(f"Processing {len(signals_df)} signals from signals_log_new.csv", level='INFO')

            # Add status column if it doesn't exist
            if 'status' not in signals_df.columns:
                signals_df['status'] = 'pending'

            # Add needed columns if they don't exist
            for col in ['exit_price', 'profit_loss']:
                if col not in signals_df.columns:
                    signals_df[col] = 0.0

            # Process each signal (similar to above)
            for idx, signal in signals_df.iterrows():
                symbol = signal.get('symbol', '')
                timestamp = signal.get('timestamp', '')

                # Skip if already in performance log with a non-pending status
                existing = perf_df[(perf_df['symbol'] == symbol) &
                                   (perf_df['timestamp'] == timestamp)]

                if len(existing) > 0 and existing['status'].iloc[0] != 'pending':
                    continue

                # Calculate success
                success = ''
                status = signal.get('status', 'pending')
                if status in ['tp1', 'tp2', 'tp3']:
                    success = 'YES'
                elif status == 'sl':
                    success = 'NO'

                # Calculate profit/loss
                profit_loss = 0.0
                if status != 'pending' and 'exit_price' in signal and 'entry' in signal:
                    try:
                        exit_price = float(signal['exit_price'])
                        entry = float(signal['entry'])
                        if entry > 0 and exit_price > 0:
                            if signal['direction'] == 'LONG':
                                profit_loss = (
                                    exit_price - entry) / entry * 100
                            else:  # SHORT
                                profit_loss = (
                                    entry - exit_price) / entry * 100
                    except:
                        pass

                # Calculate duration
                hit_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                duration_minutes = 0
                try:
                    # Fix future timestamp issue
                    if isinstance(timestamp, str) and timestamp.startswith('2025-'):
                        # If timestamp is in 2025, it's likely incorrect - extract just time part
                        time_part = timestamp.split(' ')[1]
                        # Create a new timestamp with today's date
                        timestamp = datetime.now().strftime('%Y-%m-%d') + ' ' + time_part

                    signal_time = datetime.strptime(
                        timestamp, '%Y-%m-%d %H:%M:%S')
                    duration = datetime.now() - signal_time
                    duration_minutes = int(duration.total_seconds() / 60)
                except:
                    pass

                # Create or update record
                if len(existing) == 0:
                    # New record
                    new_record = {
                        'symbol': symbol,
                        'direction': signal.get('direction', ''),
                        'timeframe': signal.get('timeframe', ''),
                        'confidence': signal.get('confidence', 0),
                        'success': success,
                        'timestamp': timestamp,
                        'entry': signal.get('entry', 0),
                        'exit_price': signal.get('exit_price', 0),
                        'tp1': signal.get('tp1', 0),
                        'tp2': signal.get('tp2', 0),
                        'tp3': signal.get('tp3', 0),
                        'sl': signal.get('sl', 0),
                        'status': status,
                        'profit_loss': round(profit_loss, 2),
                        'hit_time': hit_time,
                        'duration_minutes': duration_minutes
                    }
                    perf_df = pd.concat(
                        [perf_df, pd.DataFrame([new_record])], ignore_index=True)
                else:
                    # Update existing record
                    idx = existing.index[0]
                    perf_df.at[idx, 'status'] = status
                    perf_df.at[idx, 'success'] = success
                    perf_df.at[idx, 'hit_time'] = hit_time
                    perf_df.at[idx, 'duration_minutes'] = duration_minutes
                    perf_df.at[idx, 'exit_price'] = signal.get('exit_price', 0)
                    perf_df.at[idx, 'profit_loss'] = round(profit_loss, 2)

                    # Update other fields to ensure consistency
                    for field in ['direction', 'timeframe', 'confidence', 'entry', 'tp1', 'tp2', 'tp3', 'sl']:
                        if field in signal:
                            perf_df.at[idx, field] = signal[field]
        except Exception as e:
            log(f"Error processing signals_log_new.csv: {e}", level='ERROR')

    # Save updated performance data
    try:
        # Fix future timestamp issue in existing records
        for idx, row in perf_df.iterrows():
            timestamp = row['timestamp']
            if isinstance(timestamp, str) and timestamp.startswith('2025-'):
                # If timestamp is in 2025, it's likely incorrect - extract just time part
                time_part = timestamp.split(' ')[1]
                # Create a new timestamp with today's date
                new_timestamp = datetime.now().strftime('%Y-%m-%d') + ' ' + time_part
                perf_df.at[idx, 'timestamp'] = new_timestamp

        perf_df.to_csv(performance_log, index=False)
        new_count = len(perf_df)
        added = new_count - original_count
        log(
            f"Performance backfill complete. Added {added} new records, total {new_count} records.", level='INFO')

        # Show performance stats
        pending = len(perf_df[perf_df['status'] == 'pending'])
        completed = new_count - pending

        log(f"Performance summary: {pending} pending, {completed} completed signals", level='INFO')

        if completed > 0:
            success = len(perf_df[perf_df['success'] == 'YES'])
            success_rate = (success / completed) * 100 if completed > 0 else 0

            profit_trades = len(perf_df[perf_df['profit_loss'] > 0])
            avg_profit = perf_df[perf_df['profit_loss'] >
                                 0]['profit_loss'].mean() if profit_trades > 0 else 0

            loss_trades = len(perf_df[perf_df['profit_loss'] < 0])
            avg_loss = perf_df[perf_df['profit_loss'] <
                               0]['profit_loss'].mean() if loss_trades > 0 else 0

            log(f"Success rate: {success_rate:.2f}%", level='INFO')
            log(f"Average profit: {avg_profit:.2f}%, Average loss: {avg_loss:.2f}%", level='INFO')

    except Exception as e:
        log(f"Error saving performance data: {e}", level='ERROR')


if __name__ == "__main__":
    backfill_performance()
