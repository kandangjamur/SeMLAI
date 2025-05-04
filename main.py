import asyncio
import uvicorn
from fastapi import FastAPI
from core.analysis import fetch_ohlcv, analyze_symbol
from core.indicators import calculate_indicators
from utils.logger import log
from telebot.sender import send_telegram_signal  # Fixed import name
import ccxt.async_support as ccxt
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

CONFIDENCE_THRESHOLD = 60
TP1_POSSIBILITY_THRESHOLD = 0.8
SCALPING_CONFIDENCE_THRESHOLD = 85

@app.get("/")
async def root():
    return {"message": "Crypto Signal Bot is running."}

async def get_valid_symbols(exchange):
    try:
        markets = await exchange.load_markets()
        usdt_symbols = [s for s in markets.keys() if s.endswith('/USDT')]
        log(f"Found {len(usdt_symbols)} USDT pairs")
        return usdt_symbols
    except Exception as e:
        log(f"Error fetching symbols: {e}", level='ERROR')
        return []
    finally:
        await exchange.close()

async def scan_symbols():
    exchange = ccxt.binance({
        'apiKey': os.getenv("BINANCE_API_KEY"),
        'secret': os.getenv("BINANCE_API_SECRET"),
        'enableRateLimit': True,
    })

    if not os.getenv("BINANCE_API_KEY") or not os.getenv("BINANCE_API_SECRET"):
        log("API Key or Secret is missing!", level='ERROR')
        return

    try:
        symbols = await get_valid_symbols(exchange)
        if not symbols:
            log("No valid USDT symbols found!", level='ERROR')
            return

        for symbol in symbols:
            try:
                result = await analyze_symbol(exchange, symbol)
                if not result or not result.get('signal'):
                    log(f"⚠️ {symbol} - No valid signal")
                    continue

                confidence = result.get("confidence", 0)
                tp1_possibility = result.get("tp1_chance", 0)
                direction = result.get("signal", "none")
                trade_type = "Scalping" if confidence < SCALPING_CONFIDENCE_THRESHOLD else "Normal"

                log(f"🔍 {symbol} | Confidence: {confidence:.2f} | Direction: {direction} | TP1 Chance: {tp1_possibility:.2f}")

                if confidence >= CONFIDENCE_THRESHOLD and tp1_possibility >= TP1_POSSIBILITY_THRESHOLD:
                    signal_data = {  # Prepare data for sender.py
                        "direction": direction,
                        "confidence": confidence,
                        "price": result.get("price", 0),
                        "tp1": result.get("tp1", 0),
                        "tp2": result.get("tp2", 0),
                        "tp3": result.get("tp3", 0),
                        "sl": result.get("sl", 0),
                        "tp1_possibility": tp1_possibility * 100,  # Convert to percentage
                        "leverage": 10  # Default leverage
                    }
                    await send_telegram_signal(symbol, signal_data)  # Fixed function call
                    log("✅ Signal SENT ✅")

            except Exception as e:
                log(f"Error processing {symbol}: {e}", level='ERROR')

    except Exception as e:
        log(f"Error in scan_symbols: {e}", level='ERROR')
    finally:
        await exchange.close()

async def run_bot():
    while True:
        try:
            await scan_symbols()
        except Exception as e:
            log(f"Error in run_bot: {e}", level='ERROR')
        await asyncio.sleep(60)

if __name__ == "__main__":
    if not os.getenv("BINANCE_API_KEY") or not os.getenv("BINANCE_API_SECRET"):
        log("BINANCE_API_KEY or BINANCE_API_SECRET not set!", level='ERROR')
        exit(1)

    loop = asyncio.get_event_loop()
    loop.create_task(run_bot())
    uvicorn.run(app, host="0.0.0.0", port=8000)
