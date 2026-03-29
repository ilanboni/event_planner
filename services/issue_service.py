from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from memory import reader, writer
from memory.schema import OpenIssueSchema


async def create_issue(
    session: AsyncSession,
    event_id: str,
    domain: str,
    title: str,
    description: str,
    priority: str,
    created_by: str,
) -> OpenIssueSchema:
    return await writer.create_open_issue(
        session=session,
        event_id=event_id,
        domain=domain,
        title=title,
        description=description,
        priority=priority,
        created_by=created_by,
    )


async def update_status(
    session: AsyncSession,
    issue_id: str,
    status: str,
    note_text: str | None = None,
) -> OpenIssueSchema:
    return await writer.update_issue_status(
        session=session,
        issue_id=issue_id,
        status=status,
        note_text=note_text,
    )


async def resolve(
    session: AsyncSession,
    issue_id: str,
    decision_id: str,
) -> OpenIssueSchema:
    return await writer.resolve_issue(
        session=session,
        issue_id=issue_id,
        decision_id=decision_id,
    )


async def get_open(
    session: AsyncSession,
    event_id: str,
    priority: str | None = None,
    domain: str | None = None,
) -> list[OpenIssueSchema]:
    return await reader.load_open_issues(
        session=session,
        event_id=event_id,
        priority=priority,
        domain=domain,
    )
