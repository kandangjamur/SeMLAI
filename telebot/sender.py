# telebot/sender.py

import httpx

BOT_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

async def send_telegram_signal(message: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}

    async with httpx.AsyncClient() as client:
        await client.post(url, data=payload)
