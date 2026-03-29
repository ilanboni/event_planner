import httpx

from config import settings
from utils.logger import logger

_TELEGRAM_BASE = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"
_TELEGRAM_MAX_LENGTH = 4096


async def send_text(chat_id: int, text: str) -> None:
    """Send a plain-text message. Splits automatically if over Telegram's limit."""
    chunks = _split(text)
    async with httpx.AsyncClient(timeout=10.0) as client:
        for chunk in chunks:
            payload = {"chat_id": chat_id, "text": chunk}
            response = await client.post(f"{_TELEGRAM_BASE}/sendMessage", json=payload)
            if not response.is_success:
                logger.error(
                    "sendMessage failed chat_id=%s status=%s body=%s",
                    chat_id, response.status_code, response.text,
                )


async def send_typing_action(chat_id: int) -> None:
    """Show 'typing…' indicator in Telegram."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        await client.post(
            f"{_TELEGRAM_BASE}/sendChatAction",
            json={"chat_id": chat_id, "action": "typing"},
        )


def _split(text: str) -> list[str]:
    if len(text) <= _TELEGRAM_MAX_LENGTH:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:_TELEGRAM_MAX_LENGTH])
        text = text[_TELEGRAM_MAX_LENGTH:]
    return chunks
