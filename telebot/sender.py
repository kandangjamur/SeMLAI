# telebot/sender.py

import httpx

BOT_TOKEN = "7620836100:AAEEe4yAP18Lxxj0HoYfH8aeX4PetAxYsV0"
CHAT_ID = "-4694205383"

async def send_telegram_signal(message: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}

    async with httpx.AsyncClient() as client:
        await client.post(url, data=payload)
