import pandas as pd
import numpy as np
import os
from datetime import datetime
from utils.logger import log


async def check_tp_sl_hit(symbol, signal, current_price, tolerance=0.001):
    """Check if price hit take profit or stop loss levels"""
    try:
        direction = signal.get("direction", "")
        entry = float(signal.get("entry", 0))
        tp1 = float(signal.get("tp1", 0))
        tp2 = float(signal.get("tp2", 0))
        tp3 = float(signal.get("tp3", 0))
        sl = float(signal.get("sl", 0))
        timestamp = signal.get("timestamp", "")

        price = float(current_price)
        status = None
        hit_price = None

        # Check for hits based on direction
        if direction == "LONG":
            if price <= sl * (1 + tolerance):
                status = "sl"
                hit_price = price
                log(f"[{symbol}] 🛑 Stop Loss hit at {price}")
            elif price >= tp3 * (1 - tolerance):
                status = "tp3"
                hit_price = price
                log(f"[{symbol}] 🎯 Take Profit 3 hit at {price}")
            elif price >= tp2 * (1 - tolerance):
                status = "tp2"
                hit_price = price
                log(f"[{symbol}] 🎯 Take Profit 2 hit at {price}")
            elif price >= tp1 * (1 - tolerance):
                status = "tp1"
                hit_price = price
                log(f"[{symbol}] 🎯 Take Profit 1 hit at {price}")
        elif direction == "SHORT":
            if price >= sl * (1 - tolerance):
                status = "sl"
                hit_price = price
                log(f"[{symbol}] 🛑 Stop Loss hit at {price}")
            elif price <= tp3 * (1 + tolerance):
                status = "tp3"
                hit_price = price
                log(f"[{symbol}] 🎯 Take Profit 3 hit at {price}")
            elif price <= tp2 * (1 + tolerance):
                status = "tp2"
                hit_price = price
                log(f"[{symbol}] 🎯 Take Profit 2 hit at {price}")
            elif price <= tp1 * (1 + tolerance):
                status = "tp1"
                hit_price = price
                log(f"[{symbol}] 🎯 Take Profit 1 hit at {price}")

        # Update signal logs if we have a hit
        if status:
            # Calculate profit/loss
            profit_loss = 0.0
            if entry > 0 and hit_price is not None:
                if direction == "LONG":
                    profit_loss = (hit_price - entry) / entry * 100
                else:  # SHORT
                    profit_loss = (entry - hit_price) / entry * 100

            # Update signals log
            update_signal_log(symbol, signal, status, hit_price, profit_loss)

            # Update performance tracking
            success = "YES" if status in ["tp1", "tp2", "tp3"] else "NO"
            update_performance_log(
                symbol, signal, status, hit_price, profit_loss, success)

            return status

        return None
    except Exception as e:
        log(f"[{symbol}] Error checking TP/SL: {e}", level='ERROR')
        return None


def update_signal_log(symbol, signal, status, exit_price=None, profit_loss=0.0):
    """Update signal status in signals_log.csv"""
    try:
        csv_path = "logs/signals_log.csv"

        if not os.path.exists(csv_path):
            log(f"[{symbol}] Signal log file not found: {csv_path}", level='ERROR')
            return False

        try:
            df = pd.read_csv(csv_path)

            # Find the matching signal
            signal_time = signal.get("timestamp", "")
            mask = (df["symbol"] == symbol) & (df["timestamp"] == signal_time)

            if any(mask):
                # Update the status
                df.loc[mask, "status"] = status

                # Update exit_price if provided
                if exit_price is not None and "exit_price" in df.columns:
                    df.loc[mask, "exit_price"] = exit_price

                # Update profit/loss if calculated
                if "profit_loss" in df.columns and profit_loss != 0.0:
                    df.loc[mask, "profit_loss"] = round(profit_loss, 2)

                # Save updated dataframe
                df.to_csv(csv_path, index=False)
                log(f"[{symbol}] Signal log updated with status: {status}, profit/loss: {round(profit_loss, 2)}%")
            else:
                log(f"[{symbol}] Signal not found in log: {symbol} at {signal_time}", level='WARNING')

            # Also update the new signals log if it exists
            new_csv_path = "logs/signals_log_new.csv"
            if os.path.exists(new_csv_path):
                try:
                    new_df = pd.read_csv(new_csv_path)
                    # Add status column if it doesn't exist
                    if 'status' not in new_df.columns:
                        new_df['status'] = 'pending'

                    # Add other columns if they don't exist
                    for col in ['exit_price', 'profit_loss']:
                        if col not in new_df.columns:
                            new_df[col] = 0.0

                    # Update values for matching signal
                    new_mask = (new_df['symbol'] == symbol) & (
                        new_df['timestamp'] == signal_time)
                    if any(new_mask):
                        new_df.loc[new_mask, 'status'] = status
                        if exit_price is not None:
                            new_df.loc[new_mask, 'exit_price'] = exit_price
                        if profit_loss != 0.0:
                            new_df.loc[new_mask, "profit_loss"] = round(
                                profit_loss, 2)

                        new_df.to_csv(new_csv_path, index=False)
                        log(f"[{symbol}] New signal log also updated")
                except Exception as e:
                    log(f"[{symbol}] Error updating new signal log: {e}",
                        level='ERROR')

            return True
        except Exception as e:
            log(f"[{symbol}] Error reading/writing signal log: {e}", level='ERROR')
            return False
    except Exception as e:
        log(f"[{symbol}] Error updating signal log: {e}", level='ERROR')
        return False


def update_performance_log(symbol, signal, status, exit_price=None, profit_loss=0.0, success=""):
    """Update or add signal to performance tracking file"""
    try:
        csv_path = "logs/signal_performance.csv"

        if not os.path.exists(csv_path):
            # Create the file with headers if it doesn't exist
            columns = [
                'symbol', 'direction', 'timeframe', 'confidence', 'success',
                'timestamp', 'entry', 'exit_price', 'tp1', 'tp2', 'tp3', 'sl',
                'status', 'profit_loss', 'hit_time', 'duration_minutes'
            ]
            pd.DataFrame(columns=columns).to_csv(csv_path, index=False)
            log(f"Created performance tracking file: {csv_path}", level='INFO')

        try:
            df = pd.read_csv(csv_path)

            # Get signal details
            symbol_val = signal.get("symbol", symbol)
            timestamp = signal.get("timestamp", "")
            direction = signal.get("direction", "")
            timeframe = signal.get("timeframe", "")
            confidence = signal.get("confidence", 0)
            entry = signal.get("entry", 0)
            tp1 = signal.get("tp1", 0)
            tp2 = signal.get("tp2", 0)
            tp3 = signal.get("tp3", 0)
            sl = signal.get("sl", 0)

            # Calculate timing information
            hit_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Calculate duration in minutes
            duration_minutes = 0
            try:
                if isinstance(timestamp, str):
                    signal_time = datetime.strptime(
                        timestamp, '%Y-%m-%d %H:%M:%S')
                    duration = datetime.now() - signal_time
                    duration_minutes = int(duration.total_seconds() / 60)
                elif isinstance(timestamp, (int, float)):
                    signal_time = datetime.fromtimestamp(timestamp/1000)
                    duration = datetime.now() - signal_time
                    duration_minutes = int(duration.total_seconds() / 60)
            except Exception as e:
                log(f"[{symbol}] Error calculating duration: {e}", level='WARNING')

            # Find the matching signal
            mask = (df["symbol"] == symbol_val) & (
                df["timestamp"].astype(str) == str(timestamp))

            if any(mask):
                # Update existing record
                df.loc[mask, "status"] = status
                df.loc[mask, "hit_time"] = hit_time
                df.loc[mask, "duration_minutes"] = duration_minutes

                if success:
                    df.loc[mask, "success"] = success

                # Update exit_price and profit_loss if provided
                if exit_price is not None:
                    df.loc[mask, "exit_price"] = exit_price
                if profit_loss != 0.0:
                    df.loc[mask, "profit_loss"] = round(profit_loss, 2)

                log(f"[{symbol}] Updated performance record: {status}, P/L: {round(profit_loss, 2)}%")
            else:
                # Create a new record if not found
                new_record = {
                    'symbol': symbol_val,
                    'direction': direction,
                    'timeframe': timeframe,
                    'confidence': confidence,
                    'success': success,
                    'timestamp': timestamp,
                    'entry': entry,
                    'exit_price': exit_price if exit_price is not None else 0,
                    'tp1': tp1,
                    'tp2': tp2,
                    'tp3': tp3,
                    'sl': sl,
                    'status': status,
                    'profit_loss': round(profit_loss, 2),
                    'hit_time': hit_time,
                    'duration_minutes': duration_minutes
                }

                # Append to dataframe
                df = pd.concat([df, pd.DataFrame([new_record])],
                               ignore_index=True)
                log(f"[{symbol}] Added new performance record: {status}, P/L: {round(profit_loss, 2)}%")

            # Save updated dataframe
            df.to_csv(csv_path, index=False)
            return True
        except Exception as e:
            log(f"[{symbol}] Error processing performance log: {e}", level='ERROR')
            return False
    except Exception as e:
        log(f"[{symbol}] Error updating performance log: {e}", level='ERROR')
        return False
