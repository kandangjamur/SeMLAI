import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import joblib
import os

def train_model():
    path = "logs/signals_log.csv"
    if not os.path.exists(path):
        print("❌ signals_log.csv not found.")
        return

    df = pd.read_csv(path)

    # Drop rows with missing data
    df.dropna(inplace=True)

    # Only train on signals that have been closed (TP or SL hit)
    df = df[df["status"].isin(["TP1", "TP2", "TP3", "SL"])]

    if df.empty:
        print("⚠️ No completed signals found to train.")
        return

    # Convert result into binary (1 = Win, 0 = Loss)
    df["result"] = df["status"].apply(lambda x: 1 if "TP" in x else 0)

    # Features for training (you can expand this list as needed)
    features = ["confidence", "price", "tp1", "tp2", "tp3", "sl"]
    target = "result"

    X = df[features]
    y = df[target]

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train the model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Save the model
    os.makedirs("model", exist_ok=True)
    joblib.dump(model, "model/signal_predictor.pkl")

    acc = model.score(X_test, y_test)
    print(f"✅ Model trained with accuracy: {acc:.2f}")

if __name__ == "__main__":
    train_model()
