import os
import json
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

def extract_features(data):
    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df['return'] = df['close'].pct_change()
    df['volatility'] = (df['high'] - df['low']) / df['close']
    df['avg_volume'] = df['volume'].rolling(5).mean()
    df = df.dropna()
    return df[["return", "volatility", "avg_volume"]]

def prepare_dataset():
    path = "data/historical"
    X, y = [], []
    for file in os.listdir(path):
        if file.endswith(".json"):
            with open(os.path.join(path, file)) as f:
                data = json.load(f)
            candles = data.get("15m", [])
            if len(candles) > 20:
                features = extract_features(candles)
                X.extend(features.values)
                y.extend([1 if row[0] > 0 else 0 for row in features.values])
    return pd.DataFrame(X), y

def train_classifier():
    X, y = prepare_dataset()
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    joblib.dump(model, "model/trend_model.pkl")
    print("✅ Model trained and saved!")

if __name__ == "__main__":
    train_classifier()
