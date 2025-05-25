from utils.logger import log
import os
import sys
import pandas as pd
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def fix_future_timestamps():
    """Fix all timestamps that are incorrectly set in the future (2025)"""
    log_files = [
        "logs/signals_log.csv",
        "logs/signals_log_new.csv",
        "logs/signal_performance.csv"
    ]

    fixed_count = 0
    for file_path in log_files:
        if not os.path.exists(file_path):
            log(f"File not found: {file_path}", level="WARNING")
            continue

        # Create backup first
        backup_path = f"{file_path}.backup"
        try:
            with open(file_path, 'r') as src, open(backup_path, 'w') as dst:
                dst.write(src.read())
            log(f"Created backup: {backup_path}", level="INFO")
        except Exception as e:
            log(f"Failed to create backup of {file_path}: {e}", level="ERROR")
            continue

        # Now fix the timestamps
        try:
            df = pd.read_csv(file_path)
            if 'timestamp' not in df.columns:
                log(f"No timestamp column in {file_path}", level="WARNING")
                continue

            # Count records with future timestamps
            future_mask = df['timestamp'].astype(str).str.startswith('2025-')
            future_count = future_mask.sum()

            if future_count > 0:
                # Fix future timestamps by changing the year
                df['timestamp'] = df['timestamp'].apply(
                    lambda ts: ts.replace(
                        '2025-', '2023-') if isinstance(ts, str) and ts.startswith('2025-') else ts
                )

                # Save fixed file
                df.to_csv(file_path, index=False)
                fixed_count += future_count
                log(f"Fixed {future_count} future timestamps in {file_path}", level="INFO")
            else:
                log(f"No future timestamps found in {file_path}", level="INFO")

        except Exception as e:
            log(f"Error processing {file_path}: {e}", level="ERROR")

    log(f"Timestamp fix complete. Fixed {fixed_count} timestamps in total.", level="INFO")
    return fixed_count


if __name__ == "__main__":
    fix_future_timestamps()
