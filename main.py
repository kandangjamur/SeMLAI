import asyncio
import uvicorn
from fastapi import FastAPI
from core.analysis import fetch_ohlcv, analyze_symbol
from core.indicators import calculate_indicators
from telebot.sender import send_telegram_signal
from utils.logger import log
import ccxt.async_support as ccxt
import os
from dotenv import load_dotenv

# FastAPI ایپ
app = FastAPI()

# کنفیڈنس اور TP1 کی حد (تمہارے ڈسپلے کے مطابق)
CONFIDENCE_THRESHOLD = 60  # 60% سے زیادہ کنفیڈنس
TP1_POSSIBILITY_THRESHOLD = 0.8  # 80% سے زیادہ TP1 امکان
SCALPING_CONFIDENCE_THRESHOLD = 85  # 85 سے کم کنفیڈنس اسکیلپنگ کے لیے

# ہیلتھ چیک اینڈ پوائنٹ (روٹ)
@app.get("/")
async def root():
    return {"message": "Crypto Signal Bot is running."}

# ہیلتھ چیک اینڈ پوائنٹ (Koyeb کے لیے)
@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Bot is operational."}

# بائننس سے تمام USDT پیئرز لینے کا فنکشن
async def get_valid_symbols(exchange):
    try:
        markets = await exchange.load_markets()
        # صرف USDT پیئرز فلٹر کرو
        usdt_symbols = [s for s in markets.keys() if s.endswith('/USDT')]
        log(f"Found {len(usdt_symbols)} USDT pairs")
        return usdt_symbols
    except Exception as e:
        log(f"Error fetching symbols: {e}", level='ERROR')
        return []
    finally:
        await exchange.close()

# سگنلز سکین کرنے کا فنکشن
async def scan_symbols():
    # بائننس ایکسچینج سیٹ اپ کرو
    exchange = ccxt.binance({
        'apiKey': os.getenv("BINANCE_API_KEY"),
        'secret': os.getenv("BINANCE_API_SECRET"),
        'enableRateLimit': True,  # API ریٹ لمٹ سے بچاؤ
    })

    # API کیز چیک کرو
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    if not api_key or not api_secret:
        log("API Key or Secret is missing! Check Koyeb Config Vars.", level='ERROR')
        return

    try:
        # API کنکشن ٹیسٹ کرو
        try:
            await exchange.fetch_ticker('BTC/USDT')
            log("Binance API connection successful.")
        except Exception as e:
            log(f"Binance API connection failed: {e}", level='ERROR')
            return

        # ٹریڈنگ پیئرز لے لو
        symbols = await get_valid_symbols(exchange)
        if not symbols:
            log("No valid USDT symbols found!", level='ERROR')
            return

        for symbol in symbols:
            try:
                # ڈیٹا اور تجزیہ کرو
                result = await analyze_symbol(exchange, symbol)
                if not result or not result.get('signal'):
                    log(f"⚠️ {symbol} - No valid signal")
                    continue

                confidence = result.get("confidence", 0)
                tp1_possibility = result.get("tp1_chance", 0)
                direction = result.get("signal", "none")
                price = result.get("price", 0)
                tp1 = result.get("tp1", 0)
                tp2 = result.get("tp2", 0)
                tp3 = result.get("tp3", 0)
                sl = result.get("sl", 0)
                leverage = result.get("leverage", 10)
                trade_type = "Scalping" if confidence < SCALPING_CONFIDENCE_THRESHOLD else "Normal"

                # تمہارے اپ ڈیٹڈ ڈسپلے کے مطابق لاگنگ
                log(
                    f"🔍 {symbol} | Confidence: {confidence:.2f} | "
                    f"Direction: {direction} | TP1 Chance: {tp1_possibility:.2f} | "
                    f"Entry: {price:.4f} | TP1: {tp1:.4f} | TP2: {tp2:.4f} | "
                    f"TP3: {tp3:.4f} | SL: {sl:.4f} | Leverage: {leverage}x"
                )

                # سگنل ڈیٹا تیار کرو
                signal_data = {
                    "direction": direction,
                    "confidence": confidence,
                    "price": price,
                    "tp1": tp1,
                    "tp2": tp2,
                    "tp3": tp3,
                    "sl": sl,
                    "tp1_possibility": tp1_possibility,
                    "leverage": leverage
                }

                # اگر کنفیڈنس اور TP1 امکان حد سے زیادہ ہو، تو میسیج بھیجو
                if confidence >= CONFIDENCE_THRESHOLD and tp1_possibility >= TP1_POSSIBILITY_THRESHOLD:
                    await send_telegram_signal(symbol, signal_data)
                    log("✅ Signal SENT ✅")
                elif confidence < CONFIDENCE_THRESHOLD:
                    log("⚠️ Skipped - Low confidence")
                elif tp1_possibility < TP1_POSSIBILITY_THRESHOLD:
                    log("⚠️ Skipped - Low TP1 possibility")

                log("---")

            except Exception as e:
                log(f"Error processing {symbol}: {e}", level='ERROR')

    except Exception as e:
        log(f"Error in scan_symbols: {e}", level='ERROR')
    finally:
        await exchange.close()

# بوٹ کو مسلسل چلانے کا فنکشن
async def run_bot():
    while True:
        try:
            await scan_symbols()
        except Exception as e:
            log(f"Error in run_bot: {e}", level='ERROR')
        await asyncio.sleep(60)  # ہر منٹ سکین کرو

# مین ایپلیکیشن
if __name__ == "__main__":
    # API کیز کی دستیابی چیک کرو
    if not os.getenv("BINANCE_API_KEY") or not os.getenv("BINANCE_API_SECRET"):
        log("BINANCE_API_KEY or BINANCE_API_SECRET not set in environment!", level='ERROR')
        exit(1)

    loop = asyncio.get_event_loop()
    loop.create_task(run_bot())
    uvicorn.run(app, host="0.0.0.0", port=8000)
