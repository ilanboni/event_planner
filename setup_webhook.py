import asyncio

import httpx

from config import settings


async def register() -> None:
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook"
    payload = {
        "url": f"{settings.WEBHOOK_BASE_URL}/webhook",
        "secret_token": settings.TELEGRAM_WEBHOOK_SECRET,
        "allowed_updates": ["message"],
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload)
        data = response.json()
        if data.get("ok"):
            print(f"Webhook registered: {settings.WEBHOOK_BASE_URL}/webhook")
        else:
            print(f"Registration failed: {data}")


if __name__ == "__main__":
    asyncio.run(register())
