import os
import telegram
from dotenv import load_dotenv
from core.indicators import calculate_indicators
from core.multi_timeframe import multi_timeframe_boost
from core.candle_patterns import is_bullish_engulfing, is_breakout_candle

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = telegram.Bot(token=BOT_TOKEN)

def send_signal(signal):
    message = (
        f"🚀 Signal: {signal['symbol']}\n"
        f"🧠 Confidence: {signal['confidence']}%\n"
        f"📈 Direction: {signal['prediction']}\n"
        f"📊 Type: {signal['trade_type']}\n"
        f"📍 Entry: ${signal['price']}\n"
        f"🎯 TP1: ${signal['tp1']} ({signal['tp1_possibility']}%)\n"
        f"🎯 TP2: ${signal['tp2']} ({signal['tp2_possibility']}%)\n"
        f"🎯 TP3: ${signal['tp3']} ({signal['tp3_possibility']}%)\n"
        f"🛡 SL: ${signal['sl']}\n"
        f"⚙️ Leverage: {signal['leverage']}x\n"
    )
    bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")

def calculate_dynamic_possibilities(confidence, distance_tp1, distance_tp2, distance_tp3):
    # Example calculation for dynamic possibilities based on confidence and distance
    tp1_possibility = min(100, max(50, confidence * (1 - distance_tp1 / 100)))
    tp2_possibility = min(100, max(50, confidence * (1 - distance_tp2 / 100)))
    tp3_possibility = min(100, max(50, confidence * (1 - distance_tp3 / 100)))
    
    return tp1_possibility, tp2_possibility, tp3_possibility

def generate_trade_signal(symbol, ohlcv, exchange):
    indicators = calculate_indicators(symbol, ohlcv, exchange)
    if not indicators:
        return None

    confidence = indicators["confidence"]

    # Only generate a signal if confidence is above the threshold
    if confidence < 50:
        return None  # Discard low-confidence signals

    # Calculate the dynamic possibilities based on confidence and target distances
    distance_tp1 = indicators["tp1"] - indicators["price"]
    distance_tp2 = indicators["tp2"] - indicators["price"]
    distance_tp3 = indicators["tp3"] - indicators["price"]
    
    tp1_possibility, tp2_possibility, tp3_possibility = calculate_dynamic_possibilities(
        confidence, distance_tp1, distance_tp2, distance_tp3
    )

    # Adding prediction logic (this can be adjusted later if needed)
    prediction = "LONG" if indicators["confidence"] > 75 else "SHORT"

    # Return the dynamic signal format with calculated possibilities
    signal = {
        "symbol": indicators["symbol"],
        "confidence": confidence,
        "prediction": prediction,  # Direction based on confidence
        "trade_type": indicators["trade_type"],
        "price": indicators["price"],
        "tp1": indicators["tp1"],
        "tp2": indicators["tp2"],
        "tp3": indicators["tp3"],
        "sl": indicators["sl"],
        "leverage": indicators["leverage"],
        "tp1_possibility": tp1_possibility,
        "tp2_possibility": tp2_possibility,
        "tp3_possibility": tp3_possibility
    }
    return signal

def start_telegram_bot():
    print("📲 Telegram Bot Started")
    # Example: You can simulate a signal generation call here
    example_signal = generate_trade_signal('BTC/USDT', [], None)
    if example_signal:
        send_signal(example_signal)
