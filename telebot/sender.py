# telebot/sender.py

import httpx

async def send_telegram_signal(message: str):
    bot_token = "YOUR_BOT_TOKEN"
    chat_id = "YOUR_CHAT_ID"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}

    async with httpx.AsyncClient() as client:
        await client.post(url, data=payload)
