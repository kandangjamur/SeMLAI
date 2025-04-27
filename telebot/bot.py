import os
import telegram
import random
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
    tp1_possibility = min(100, max(50, confidence * (1 - distance_tp1 / 100)))
    tp2_possibility = min(100, max(50, confidence * (1 - distance_tp2 / 100)))
    tp3_possibility = min(100, max(50, confidence * (1 - distance_tp3 / 100)))
    
    return tp1_possibility, tp2_possibility, tp3_possibility

def calculate_dynamic_leverage(confidence):
    if 70 <= confidence < 85:
        return random.choice(range(20, 31))  # Scalping 20x-30x
    elif 85 <= confidence <= 100:
        return random.choice(range(10, 21))  # Normal Trade 10x-20x
    else:
        return 10  # fallback (should not happen because we filter below 70)

def generate_trade_signal(symbol, ohlcv, exchange):
    try:
        indicators = calculate_indicators(symbol, ohlcv, exchange)
        if not indicators:
            return None

        confidence = indicators.get("confidence")
        if confidence is None or confidence < 70:
            return None  # Discard low-confidence or invalid signals

        price = indicators.get("price")
        tp1 = indicators.get("tp1")
        tp2 = indicators.get("tp2")
        tp3 = indicators.get("tp3")
        sl = indicators.get("sl")

        # Validate important fields
        if None in (price, tp1, tp2, tp3, sl):
            return None

        # Calculate dynamic possibilities
        distance_tp1 = tp1 - price
        distance_tp2 = tp2 - price
        distance_tp3 = tp3 - price

        tp1_possibility, tp2_possibility, tp3_possibility = calculate_dynamic_possibilities(
            confidence, distance_tp1, distance_tp2, distance_tp3
        )

        # Trade Type based on confidence
        if 70 <= confidence < 85:
            trade_type = "Scalping"
        else:
            trade_type = "Normal Trade"

        # Prediction based on direction
        prediction = "LONG" if confidence >= 85 else "SHORT"

        # Dynamic leverage calculation
        leverage = indicators.get("leverage")
        if leverage is None:
            leverage = calculate_dynamic_leverage(confidence)

        signal = {
            "symbol": indicators["symbol"],
            "confidence": confidence,
            "prediction": prediction,
            "trade_type": trade_type,
            "price": price,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "sl": sl,
            "leverage": leverage,
            "tp1_possibility": round(tp1_possibility, 2),
            "tp2_possibility": round(tp2_possibility, 2),
            "tp3_possibility": round(tp3_possibility, 2)
        }
        return signal

    except Exception as e:
        print(f"⚠️ Error generating trade signal for {symbol}: {e}")
        return None

def start_telegram_bot():
    print("📲 Telegram Bot Started")
    example_signal = generate_trade_signal('BTC/USDT', [], None)
    if example_signal:
        send_signal(example_signal)
