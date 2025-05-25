import os
import sys
import pandas as pd
import ccxt
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler(
        'logs/signal_updater.log')]
)
logger = logging.getLogger()


class SignalStatusUpdater:
    def __init__(self):
        self.exchange = ccxt.binance({
            'enableRateLimit': True
        })
        self.performance_file = "logs/signal_performance.csv"

    def update_signal_statuses(self):
        """Update all pending signals with current market prices"""
        logger.info("Starting signal status update...")

        if not os.path.exists(self.performance_file):
            logger.error(
                f"Performance file not found: {self.performance_file}")
            return False

        try:
            # Load performance data
            perf_df = pd.read_csv(self.performance_file)

            # Get pending signals
            pending_signals = perf_df[perf_df['status'] == 'pending']
            logger.info(
                f"Found {len(pending_signals)} pending signals to check")

            if len(pending_signals) == 0:
                logger.info("No pending signals to update")
                return True

            # Process each pending signal
            updates = 0
            for idx, signal in pending_signals.iterrows():
                symbol = signal['symbol']
                direction = signal['direction']
                entry = float(signal['entry'])
                tp1 = float(signal['tp1'])
                tp2 = float(signal['tp2'])
                tp3 = float(signal['tp3'])
                sl = float(signal['sl'])

                try:
                    # Get current price
                    ticker = self.exchange.fetch_ticker(symbol)
                    current_price = ticker['last']
                    logger.info(
                        f"Checking {symbol} {direction}: Entry={entry}, Current={current_price}")

                    # Check if any target has been hit
                    status = 'pending'
                    exit_price = 0
                    profit_loss = 0
                    success = ''

                    if direction == 'LONG':
                        # Check stop loss
                        if current_price <= sl:
                            status = 'sl'
                            exit_price = sl
                            profit_loss = (sl - entry) / entry * 100
                            success = 'NO'
                        # Check take profits
                        elif current_price >= tp3:
                            status = 'tp3'
                            exit_price = tp3
                            profit_loss = (tp3 - entry) / entry * 100
                            success = 'YES'
                        elif current_price >= tp2:
                            status = 'tp2'
                            exit_price = tp2
                            profit_loss = (tp2 - entry) / entry * 100
                            success = 'YES'
                        elif current_price >= tp1:
                            status = 'tp1'
                            exit_price = tp1
                            profit_loss = (tp1 - entry) / entry * 100
                            success = 'YES'
                    else:  # SHORT
                        # Check stop loss
                        if current_price >= sl:
                            status = 'sl'
                            exit_price = sl
                            profit_loss = (entry - sl) / entry * 100
                            success = 'NO'
                        # Check take profits
                        elif current_price <= tp3:
                            status = 'tp3'
                            exit_price = tp3
                            profit_loss = (entry - tp3) / entry * 100
                            success = 'YES'
                        elif current_price <= tp2:
                            status = 'tp2'
                            exit_price = tp2
                            profit_loss = (entry - tp2) / entry * 100
                            success = 'YES'
                        elif current_price <= tp1:
                            status = 'tp1'
                            exit_price = tp1
                            profit_loss = (entry - tp1) / entry * 100
                            success = 'YES'

                    # Update signal if status changed
                    if status != 'pending':
                        hit_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                        # Calculate duration
                        try:
                            signal_time = datetime.strptime(
                                signal['timestamp'], '%Y-%m-%d %H:%M:%S')
                            duration = datetime.now() - signal_time
                            duration_minutes = int(
                                duration.total_seconds() / 60)
                        except Exception as e:
                            logger.warning(
                                f"Error calculating duration for {symbol}: {str(e)}")
                            duration_minutes = 0

                        # Update performance record
                        perf_df.at[idx, 'status'] = status
                        perf_df.at[idx, 'exit_price'] = exit_price
                        perf_df.at[idx, 'profit_loss'] = round(profit_loss, 2)
                        perf_df.at[idx, 'success'] = success
                        perf_df.at[idx, 'hit_time'] = hit_time
                        perf_df.at[idx, 'duration_minutes'] = duration_minutes

                        logger.info(
                            f"Updated {symbol} {direction}: Status={status}, P/L={round(profit_loss, 2)}%, Current price={current_price}")
                        updates += 1

                except Exception as e:
                    logger.error(f"Error updating {symbol}: {str(e)}")

            # Save updated performance data
            if updates > 0:
                perf_df.to_csv(self.performance_file, index=False)
                logger.info(f"Updated {updates} signals in performance file")

            return True

        except Exception as e:
            logger.error(f"Error updating signals: {str(e)}")
            return False


if __name__ == "__main__":
    updater = SignalStatusUpdater()
    updater.update_signal_statuses()
