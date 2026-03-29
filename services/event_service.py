from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Event


async def get_event_by_telegram_id(session: AsyncSession, telegram_id: str | int) -> Event | None:
    result = await session.execute(
        select(Event).where(Event.client_telegram_id == str(telegram_id))
    )
    return result.scalar_one_or_none()


async def get_event_by_id(session: AsyncSession, event_id: str) -> Event | None:
    result = await session.execute(
        select(Event).where(Event.id == event_id)
    )
    return result.scalar_one_or_none()


async def update_event_fields(session: AsyncSession, event_id: str, **fields) -> Event | None:
    event = await get_event_by_id(session, event_id)
    if event is None:
        return None
    for key, value in fields.items():
        if hasattr(event, key):
            setattr(event, key, value)
    event.updated_at = datetime.utcnow()
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event
