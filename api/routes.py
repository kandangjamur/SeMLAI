from flask import Flask, jsonify
from core.analysis import generate_signals

app = Flask(__name__)

@app.route('/get_signals', methods=['GET'])
def get_signals():
    signals = generate_signals()
    return jsonify(signals)
