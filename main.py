from flask import Flask
from core.analysis import generate_signals
import schedule
import time

app = Flask(__name__)

@app.route('/')
def home():
    return "Crypto Signal Bot is running!"

def schedule_signals():
    # Automatically generate signals for all USDT pairs at intervals (e.g., every minute)
    schedule.every(1).minute.do(generate_signals)

if __name__ == '__main__':
    schedule_signals()
    app.run(debug=True, host='0.0.0.0', port=5000)
