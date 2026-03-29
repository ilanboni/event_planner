from fastapi import APIRouter, Header, HTTPException, Request

from bot.message_handler import handle_update
from config import settings
from utils.logger import logger

router = APIRouter()


@router.post("/webhook")
async def webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        logger.warning("Webhook called with invalid secret token")
        raise HTTPException(status_code=403, detail="Forbidden")

    body = await request.json()
    await handle_update(body)

    # Telegram requires a fast 200 OK.
    # In Phase 4, move handle_update into a BackgroundTask when LLM calls are added.
    return {"ok": True}
