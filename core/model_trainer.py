# core/model_trainer.py

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import StandardScaler
import joblib

def train_model(data):
    """
    Train a machine learning model to predict the market trend.
    
    :param data: Historical market data (with labels for buy/sell/hold)
    :return: Trained model
    """
    
    # Example of feature columns (these would be your technical indicators)
    features = ['rsi', 'macd', 'macd_signal', 'short_ema', 'long_ema']
    target = 'signal'  # The target column (buy/sell/hold signal)

    # Data preparation
    X = data[features]
    y = data[target]

    # Normalize the feature data
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Split data into training and test sets (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    # Initialize the classifier (Random Forest Classifier as an example)
    model = RandomForestClassifier(n_estimators=100, random_state=42)

    # Train the model
    model.fit(X_train, y_train)

    # Predict on the test set
    y_pred = model.predict(X_test)

    # Evaluate the model
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model Accuracy: {accuracy * 100:.2f}%")

    # Save the trained model to disk
    joblib.dump(model, 'model.pkl')
    joblib.dump(scaler, 'scaler.pkl')  # Save the scaler as well
    
    return model, scaler

def load_trained_model():
    """
    Load a pre-trained model from disk.
    
    :return: Trained model and scaler
    """
    model = joblib.load('model.pkl')
    scaler = joblib.load('scaler.pkl')
    
    return model, scaler

def predict(model, scaler, data):
    """
    Use the trained model to predict signals based on new market data.
    
    :param model: Trained machine learning model
    :param scaler: StandardScaler used during training
    :param data: New market data (with features)
    :return: Predicted signal
    """
    
    # Normalize the new data
    data_scaled = scaler.transform(data)
    
    # Predict the signal (buy/sell/hold)
    signal = model.predict(data_scaled)
    
    return signal
