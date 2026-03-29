from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

from bot.message_handler import handle_update
from config import settings
from utils.logger import logger

router = APIRouter()


@router.post("/webhook")
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    if x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        logger.warning("Webhook called with invalid secret token")
        raise HTTPException(status_code=403, detail="Forbidden")

    body = await request.json()

    # Return 200 OK to Telegram immediately, process in background.
    # This prevents Telegram from retrying the request if the LLM pipeline
    # takes longer than Telegram's 60-second webhook timeout.
    background_tasks.add_task(handle_update, body)

    return {"ok": True}
