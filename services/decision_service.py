from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from memory import reader, writer
from memory.schema import ConfirmedDecisionSchema


async def create_decision(
    session: AsyncSession,
    event_id: str,
    domain: str,
    title: str,
    description: str,
    source: str,
    decided_by: str,
    supersedes_id: str | None = None,
    notes: str | None = None,
) -> ConfirmedDecisionSchema:
    return await writer.write_confirmed_decision(
        session=session,
        event_id=event_id,
        domain=domain,
        title=title,
        description=description,
        source=source,
        decided_by=decided_by,
        supersedes_id=supersedes_id,
        notes=notes,
    )


async def get_decisions(
    session: AsyncSession,
    event_id: str,
    domain: str | None = None,
    active_only: bool = True,
) -> list[ConfirmedDecisionSchema]:
    return await reader.load_confirmed_decisions(
        session=session,
        event_id=event_id,
        domain=domain,
        active_only=active_only,
    )


async def get_recent_decisions(
    session: AsyncSession,
    event_id: str,
    limit: int = 5,
) -> list[ConfirmedDecisionSchema]:
    return await reader.load_recent_decisions(session=session, event_id=event_id, limit=limit)
