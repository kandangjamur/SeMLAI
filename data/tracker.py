import csv
import os
import ccxt
import time
from datetime import datetime

def update_signal_status():
    log_path = "logs/signals_log.csv"
    if not os.path.exists(log_path):
        print("❌ Log file not found.")
        return

    exchange = ccxt.binance()
    updated_rows = []

    with open(log_path, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for row in rows:
        if row["status"] != "OPEN":
            updated_rows.append(row)
            continue

        symbol = row["symbol"].replace("USDT/", "") + "/USDT"
        try:
            ticker = exchange.fetch_ticker(symbol)
            price = ticker["last"]
        except:
            print(f"❌ Could not fetch price for {symbol}")
            updated_rows.append(row)
            continue

        tp1 = float(row["tp1"])
        tp2 = float(row["tp2"])
        tp3 = float(row["tp3"])
        sl = float(row["sl"])
        direction = row["direction"]

        status = row["status"]

        if direction == "LONG":
            if price >= tp3:
                status = "TP3"
            elif price >= tp2:
                status = "TP2"
            elif price >= tp1:
                status = "TP1"
            elif price <= sl:
                status = "SL"
        elif direction == "SHORT":
            if price <= tp3:
                status = "TP3"
            elif price <= tp2:
                status = "TP2"
            elif price <= tp1:
                status = "TP1"
            elif price >= sl:
                status = "SL"

        row["status"] = status
        updated_rows.append(row)
        print(f"[TRACKER] {symbol} → {status}")

    with open(log_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(updated_rows)

# Optional: Run every 10 mins
if __name__ == "__main__":
    while True:
        print(f"🕵️ Checking TP/SL status... {datetime.now()}")
        update_signal_status()
        time.sleep(600)
