from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from bot.sender import send_text, send_typing_action
from db.models import Message
from db.session import AsyncSessionLocal
from services import event_service
from utils.enums import AttachmentType, MessageDirection
from utils.logger import logger

_ONBOARDING_TEXT = (
    "Ciao, sono Marcy. Non sei ancora registrata nel sistema — "
    "contatta il coordinatore per essere aggiunta."
)


@dataclass
class TelegramAttachment:
    file_id: str
    file_unique_id: str
    telegram_type: AttachmentType
    mime_type: str | None
    file_name: str | None
    file_size: int | None


@dataclass
class IncomingMessage:
    telegram_message_id: int
    chat_id: int
    user_id: int
    text: str | None
    attachments: list[TelegramAttachment] = field(default_factory=list)
    reply_to_message_id: int | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


def normalize_update(update: dict) -> IncomingMessage | None:
    """
    Convert a raw Telegram Update dict into an IncomingMessage.
    Returns None for update types we do not handle.
    """
    message = update.get("message")
    if not message:
        return None

    sender = message.get("from", {})
    reply_to = message.get("reply_to_message")
    text = message.get("text") or message.get("caption")

    return IncomingMessage(
        telegram_message_id=message["message_id"],
        chat_id=message["chat"]["id"],
        user_id=sender.get("id", 0),
        text=text,
        attachments=_parse_attachments(message),
        reply_to_message_id=reply_to["message_id"] if reply_to else None,
        timestamp=datetime.utcfromtimestamp(message["date"]),
    )


def _parse_attachments(message: dict) -> list[TelegramAttachment]:
    attachments = []

    if doc := message.get("document"):
        attachments.append(TelegramAttachment(
            file_id=doc["file_id"],
            file_unique_id=doc["file_unique_id"],
            telegram_type=AttachmentType.DOCUMENT,
            mime_type=doc.get("mime_type"),
            file_name=doc.get("file_name"),
            file_size=doc.get("file_size"),
        ))

    if photos := message.get("photo"):
        photo = photos[-1]  # Highest resolution
        attachments.append(TelegramAttachment(
            file_id=photo["file_id"],
            file_unique_id=photo["file_unique_id"],
            telegram_type=AttachmentType.PHOTO,
            mime_type="image/jpeg",
            file_name=None,
            file_size=photo.get("file_size"),
        ))

    if audio := message.get("audio"):
        attachments.append(TelegramAttachment(
            file_id=audio["file_id"],
            file_unique_id=audio["file_unique_id"],
            telegram_type=AttachmentType.AUDIO,
            mime_type=audio.get("mime_type"),
            file_name=audio.get("file_name"),
            file_size=audio.get("file_size"),
        ))

    return attachments


async def _save_message(
    session,
    event_id: str | None,
    msg: IncomingMessage,
    direction: MessageDirection,
    text: str | None,
) -> None:
    record = Message(
        event_id=event_id,
        telegram_message_id=msg.telegram_message_id if direction == MessageDirection.INCOMING else None,
        chat_id=msg.chat_id,
        user_id=msg.user_id if direction == MessageDirection.INCOMING else None,
        direction=direction.value,
        text=text,
    )
    session.add(record)
    await session.commit()


async def handle_update(update: dict) -> None:
    msg = normalize_update(update)

    if msg is None:
        logger.debug("Ignored update keys=%s", list(update.keys()))
        return

    logger.info(
        "Message received chat_id=%s text=%r attachments=%d",
        msg.chat_id, msg.text, len(msg.attachments),
    )

    async with AsyncSessionLocal() as session:
        event = await event_service.get_event_by_telegram_id(session, msg.chat_id)
        event_id = event.id if event else None

        # Save incoming message
        await _save_message(session, event_id, msg, MessageDirection.INCOMING, msg.text)

        await send_typing_action(msg.chat_id)

        if event is None:
            reply = _ONBOARDING_TEXT
        else:
            from orchestrator.pipeline import process
            reply = await process(msg, event_id)

        await send_text(msg.chat_id, reply)

        # Save outgoing message
        await _save_message(session, event_id, msg, MessageDirection.OUTGOING, reply)
