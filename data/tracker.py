import pandas as pd
import os

def update_signal_status():
    filename = "logs/signals_log.csv"
    if not os.path.exists(filename):
        return
    df = pd.read_csv(filename)
    df.to_csv(filename, index=False)
