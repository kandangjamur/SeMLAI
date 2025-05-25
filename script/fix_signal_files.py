import os
import sys
import pandas as pd
import logging

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
log = logging.getLogger("crypto-signal-bot")


def fix_signal_files():
    """Fix CSV signal files with inconsistent columns"""
    log.info("Starting signal files fix")

    # List of signal files to check
    signal_files = [
        os.path.join(parent_dir, "logs/signals_log.csv"),
        os.path.join(parent_dir, "logs/signals_log_new.csv"),
        os.path.join(parent_dir, "logs/signal_performance.csv")
    ]

    # Required columns for each file
    required_columns = {
        "signals_log.csv": [
            "symbol", "direction", "confidence", "entry", "tp1", "tp2", "tp3", "sl",
            "timestamp", "timeframe", "status", "exit_price", "profit_loss"
        ],
        "signals_log_new.csv": [
            "symbol", "direction", "confidence", "entry", "tp1", "tp2", "tp3", "sl",
            "timestamp", "timeframe", "status", "exit_price", "profit_loss"
        ],
        "signal_performance.csv": [
            "symbol", "direction", "timeframe", "confidence", "success",
            "timestamp", "entry", "exit_price", "tp1", "tp2", "tp3", "sl",
            "status", "profit_loss", "hit_time", "duration_minutes"
        ]
    }

    # Process each file
    for file_path in signal_files:
        if not os.path.exists(file_path):
            log.warning(f"File not found: {file_path}")
            continue

        file_name = os.path.basename(file_path)

        try:
            # Try to read file with error handling - using on_bad_lines parameter instead of error_bad_lines
            # on_bad_lines='warn' replaces warn_bad_lines=True
            # on_bad_lines='skip' replaces error_bad_lines=False
            df = pd.read_csv(file_path, on_bad_lines='skip')
            log.info(f"Successfully loaded {file_name} with {len(df)} rows")

            # Check columns
            if file_name in required_columns:
                required = required_columns[file_name]

                # Add missing columns
                for col in required:
                    if col not in df.columns:
                        if col in ['status', 'success']:
                            df[col] = 'pending'
                        elif col in ['confidence', 'profit_loss']:
                            df[col] = 0.0
                        elif col in ['timestamp', 'hit_time']:
                            df[col] = '2025-05-01 00:00:00'
                        else:
                            df[col] = ''
                        log.info(
                            f"Added missing column '{col}' to {file_name}")

                # Reorder columns
                df = df[required + [c for c in df.columns if c not in required]]

                # Save back the fixed file with backup
                backup_path = file_path + '.bak'
                os.rename(file_path, backup_path)
                df.to_csv(file_path, index=False)
                log.info(
                    f"Fixed and saved {file_name} with {len(df.columns)} columns")

        except Exception as e:
            log.error(f"Error processing {file_name}: {str(e)}")

            # Try manual fix
            try:
                with open(file_path, 'r') as f:
                    lines = f.readlines()

                # Get header line
                header = lines[0].strip()
                headers = header.split(',')

                # Fix required columns
                if file_name in required_columns:
                    fixed_headers = required_columns[file_name]
                    missing_headers = [
                        h for h in fixed_headers if h not in headers]

                    if missing_headers:
                        new_header = header + ',' + ','.join(missing_headers)
                        lines[0] = new_header + '\n'

                        # Add empty values for new columns
                        for i in range(1, len(lines)):
                            lines[i] = lines[i].strip() + ',' + \
                                ','.join([''] * len(missing_headers)) + '\n'

                    # Write fixed file
                    backup_path = file_path + '.bak'
                    os.rename(file_path, backup_path)
                    with open(file_path, 'w') as f:
                        f.writelines(lines)
                    log.info(f"Manually fixed {file_name}")

            except Exception as manual_err:
                log.error(
                    f"Manual fix failed for {file_name}: {str(manual_err)}")

    log.info("Signal files fix completed")


if __name__ == "__main__":
    fix_signal_files()
