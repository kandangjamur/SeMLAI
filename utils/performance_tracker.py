import os
import pandas as pd
from datetime import datetime
import logging
from utils.logger import log


class PerformanceTracker:
    def __init__(self):
        self.performance_file = "logs/signal_performance.csv"
        self.signals_log = "logs/signals_log.csv"
        self.signals_log_new = "logs/signals_log_new.csv"
        self.ensure_files_exist()

    def ensure_files_exist(self):
        """Make sure all necessary log files exist"""
        # Performance tracking file
        if not os.path.exists(self.performance_file):
            columns = [
                'symbol', 'direction', 'timeframe', 'confidence', 'success',
                'timestamp', 'entry', 'exit_price', 'tp1', 'tp2', 'tp3', 'sl',
                'status', 'profit_loss', 'hit_time', 'duration_minutes'
            ]
            pd.DataFrame(columns=columns).to_csv(
                self.performance_file, index=False)
            log(f"Created performance tracking file: {self.performance_file}")

        # Signal logs
        for logfile in [self.signals_log, self.signals_log_new]:
            if not os.path.exists(logfile):
                columns = [
                    'symbol', 'direction', 'timeframe', 'confidence',
                    'timestamp', 'entry', 'sl', 'tp1', 'tp2', 'tp3',
                    'status', 'exit_price', 'profit_loss'
                ]
                pd.DataFrame(columns=columns).to_csv(logfile, index=False)
                log(f"Created signal log file: {logfile}")

    def add_signal(self, signal):
        """Add a new signal to performance tracking"""
        try:
            # Format signal for performance tracking
            perf_record = {
                'symbol': signal.get('symbol', ''),
                'direction': signal.get('direction', ''),
                'timeframe': signal.get('timeframe', ''),
                'confidence': signal.get('confidence', 0),
                'success': '',
                'timestamp': signal.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                'entry': signal.get('entry', 0),
                'exit_price': 0,
                'tp1': signal.get('tp1', 0),
                'tp2': signal.get('tp2', 0),
                'tp3': signal.get('tp3', 0),
                'sl': signal.get('sl', 0),
                'status': 'pending',
                'profit_loss': 0,
                'hit_time': '',
                'duration_minutes': 0
            }

            # Load existing data
            if os.path.exists(self.performance_file):
                df = pd.read_csv(self.performance_file)

                # Check if this signal already exists
                mask = (df['symbol'] == perf_record['symbol']) & (
                    df['timestamp'] == perf_record['timestamp'])
                if any(mask):
                    log(f"[{perf_record['symbol']}] Signal already exists in performance tracking")
                    return False

                # Add new record
                df = pd.concat(
                    [df, pd.DataFrame([perf_record])], ignore_index=True)
            else:
                df = pd.DataFrame([perf_record])

            # Save updated dataframe
            df.to_csv(self.performance_file, index=False)
            log(f"[{perf_record['symbol']}] Added to performance tracking")
            return True

        except Exception as e:
            log(
                f"Error adding signal to performance tracking: {e}", level='ERROR')
            return False

    def update_signal_status(self, symbol, timestamp, status, exit_price=None, profit_loss=None, success=None):
        """Update status of an existing signal"""
        try:
            if not os.path.exists(self.performance_file):
                log(
                    f"Performance file not found: {self.performance_file}", level='ERROR')
                return False

            df = pd.read_csv(self.performance_file)

            # Find the signal
            mask = (df['symbol'] == symbol) & (
                df['timestamp'].astype(str) == str(timestamp))

            if any(mask):
                # Update status
                df.loc[mask, 'status'] = status

                # Update other fields if provided
                if exit_price is not None:
                    df.loc[mask, 'exit_price'] = exit_price

                if profit_loss is not None:
                    df.loc[mask, 'profit_loss'] = profit_loss

                if success is not None:
                    df.loc[mask, 'success'] = success

                # Update hit time and duration if status is not pending
                if status != 'pending':
                    hit_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    df.loc[mask, 'hit_time'] = hit_time

                    # Calculate duration
                    try:
                        signal_time = datetime.strptime(
                            str(timestamp).split('.')[0], '%Y-%m-%d %H:%M:%S')
                        duration = (datetime.now() -
                                    signal_time).total_seconds() / 60
                        df.loc[mask, 'duration_minutes'] = int(duration)
                    except Exception as e:
                        log(f"Error calculating duration: {e}",
                            level='WARNING')

                # Save updated dataframe
                df.to_csv(self.performance_file, index=False)
                log(f"[{symbol}] Updated status to {status}")
                return True
            else:
                log(f"[{symbol}] Signal not found in performance tracking",
                    level='WARNING')
                return False

        except Exception as e:
            log(f"Error updating signal status: {e}", level='ERROR')
            return False

    def sync_pending_signals(self):
        """Sync signals from logs to performance tracking"""
        try:
            log("Syncing pending signals to performance tracking...")

            # Ensure performance file exists
            self.ensure_files_exist()

            # Load performance data
            perf_df = pd.read_csv(self.performance_file)

            # Process each signal log
            for logfile in [self.signals_log, self.signals_log_new]:
                if os.path.exists(logfile):
                    try:
                        log_df = pd.read_csv(logfile)
                        added = 0

                        for _, signal in log_df.iterrows():
                            if 'symbol' not in signal or 'timestamp' not in signal:
                                continue

                            # Check if signal exists in performance tracking
                            symbol = signal['symbol']
                            timestamp = signal['timestamp']

                            mask = (perf_df['symbol'] == symbol) & (
                                perf_df['timestamp'].astype(str) == str(timestamp))

                            if not any(mask):
                                # Add to performance tracking
                                perf_record = {
                                    'symbol': symbol,
                                    'direction': signal.get('direction', ''),
                                    'timeframe': signal.get('timeframe', ''),
                                    'confidence': signal.get('confidence', 0),
                                    'success': '',
                                    'timestamp': timestamp,
                                    'entry': signal.get('entry', 0),
                                    'exit_price': signal.get('exit_price', 0),
                                    'tp1': signal.get('tp1', 0),
                                    'tp2': signal.get('tp2', 0),
                                    'tp3': signal.get('tp3', 0),
                                    'sl': signal.get('sl', 0),
                                    'status': signal.get('status', 'pending'),
                                    'profit_loss': signal.get('profit_loss', 0),
                                    'hit_time': '',
                                    'duration_minutes': 0
                                }

                                perf_df = pd.concat(
                                    [perf_df, pd.DataFrame([perf_record])], ignore_index=True)
                                added += 1

                        if added > 0:
                            log(f"Added {added} signals from {logfile} to performance tracking")

                    except Exception as e:
                        log(f"Error syncing from {logfile}: {e}",
                            level='ERROR')

            # Save updated performance data
            if 'added' in locals() and added > 0:
                perf_df.to_csv(self.performance_file, index=False)
                log("Performance tracking sync complete")
            else:
                log("No new signals to sync")

        except Exception as e:
            log(f"Error syncing pending signals: {e}", level='ERROR')

    async def sync_to_signal_logs(self):
        """Update signal logs with latest status from performance tracking"""
        try:
            if not os.path.exists(self.performance_file):
                log("Performance file not found", level='WARNING')
                return

            # Load performance data
            perf_df = pd.read_csv(self.performance_file)

            # Process each signal log
            for logfile in [self.signals_log, self.signals_log_new]:
                if os.path.exists(logfile):
                    try:
                        log_df = pd.read_csv(logfile)
                        updates = 0

                        for idx, signal in log_df.iterrows():
                            symbol = signal.get('symbol', '')
                            timestamp = signal.get('timestamp', '')

                            # Find matching record in performance data
                            mask = (perf_df['symbol'] == symbol) & (
                                perf_df['timestamp'].astype(str) == str(timestamp))

                            if any(mask):
                                perf_record = perf_df[mask].iloc[0]

                                # Update status and other fields if they differ
                                if ('status' in log_df.columns and signal.get('status', '') != perf_record['status']) or \
                                   ('exit_price' in log_df.columns and signal.get('exit_price', 0) != perf_record['exit_price']) or \
                                   ('profit_loss' in log_df.columns and signal.get('profit_loss', 0) != perf_record['profit_loss']):

                                    # Update fields
                                    if 'status' in log_df.columns:
                                        log_df.at[idx,
                                                  'status'] = perf_record['status']
                                    if 'exit_price' in log_df.columns:
                                        log_df.at[idx,
                                                  'exit_price'] = perf_record['exit_price']
                                    if 'profit_loss' in log_df.columns:
                                        log_df.at[idx,
                                                  'profit_loss'] = perf_record['profit_loss']

                                    updates += 1

                        if updates > 0:
                            log_df.to_csv(logfile, index=False)
                            log(f"Updated {updates} signals in {logfile}")

                    except Exception as e:
                        log(f"Error updating {logfile}: {e}", level='ERROR')

        except Exception as e:
            log(f"Error syncing to signal logs: {e}", level='ERROR')
