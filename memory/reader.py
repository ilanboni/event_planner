from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    BudgetSummary, ClientProfile, ConfirmedDecision, DesignBrief,
    Event, FileRecord, GuestSummary, OpenIssue, TimelineDraft,
    TimelineItem, Vendor, WorkingNotes,
)
from memory.schema import (
    BudgetSummarySchema, ClientProfileSchema, ConfirmedDecisionSchema,
    DesignBriefSchema, EventCoreSchema, FileRecordSchema, GuestSummarySchema,
    OpenIssueSchema, TimelineDraftSchema, TimelineItemSchema, VendorSchema,
    WorkingNotesSchema,
)

_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


async def load_event_core(session: AsyncSession, event_id: str) -> EventCoreSchema | None:
    result = await session.execute(select(Event).where(Event.id == event_id))
    row = result.scalar_one_or_none()
    return EventCoreSchema.model_validate(row) if row else None


async def load_client_profile(session: AsyncSession, event_id: str) -> ClientProfileSchema | None:
    result = await session.execute(
        select(ClientProfile).where(ClientProfile.event_id == event_id)
    )
    row = result.scalar_one_or_none()
    return ClientProfileSchema.model_validate(row) if row else None


async def load_confirmed_decisions(
    session: AsyncSession,
    event_id: str,
    domain: str | None = None,
    active_only: bool = True,
    limit: int | None = None,
) -> list[ConfirmedDecisionSchema]:
    stmt = (
        select(ConfirmedDecision)
        .where(ConfirmedDecision.event_id == event_id)
    )
    if active_only:
        stmt = stmt.where(ConfirmedDecision.is_active.is_(True))
    if domain:
        stmt = stmt.where(ConfirmedDecision.domain == domain)
    stmt = stmt.order_by(ConfirmedDecision.created_at.desc())
    if limit:
        stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return [ConfirmedDecisionSchema.model_validate(r) for r in result.scalars().all()]


async def load_recent_decisions(
    session: AsyncSession,
    event_id: str,
    limit: int = 5,
) -> list[ConfirmedDecisionSchema]:
    return await load_confirmed_decisions(session, event_id, active_only=True, limit=limit)


async def load_open_issues(
    session: AsyncSession,
    event_id: str,
    priority: str | None = None,
    domain: str | None = None,
) -> list[OpenIssueSchema]:
    stmt = (
        select(OpenIssue)
        .where(OpenIssue.event_id == event_id)
        .where(OpenIssue.status.notin_(["resolved", "deferred"]))
    )
    if priority:
        stmt = stmt.where(OpenIssue.priority == priority)
    if domain:
        stmt = stmt.where(OpenIssue.domain == domain)
    stmt = stmt.order_by(OpenIssue.created_at.asc())
    result = await session.execute(stmt)
    issues = [OpenIssueSchema.model_validate(r) for r in result.scalars().all()]
    issues.sort(key=lambda i: _PRIORITY_ORDER.get(i.priority, 3))
    return issues


async def load_vendors(
    session: AsyncSession,
    event_id: str,
    category: str | None = None,
    status: str | None = None,
) -> list[VendorSchema]:
    stmt = select(Vendor).where(Vendor.event_id == event_id)
    if category:
        stmt = stmt.where(Vendor.category == category)
    if status:
        stmt = stmt.where(Vendor.status == status)
    stmt = stmt.order_by(Vendor.created_at.asc())
    result = await session.execute(stmt)
    return [VendorSchema.model_validate(r) for r in result.scalars().all()]


async def load_budget_summary(session: AsyncSession, event_id: str) -> BudgetSummarySchema | None:
    result = await session.execute(
        select(BudgetSummary).where(BudgetSummary.event_id == event_id)
    )
    row = result.scalar_one_or_none()
    return BudgetSummarySchema.model_validate(row) if row else None


async def load_guest_summary(session: AsyncSession, event_id: str) -> GuestSummarySchema | None:
    result = await session.execute(
        select(GuestSummary).where(GuestSummary.event_id == event_id)
    )
    row = result.scalar_one_or_none()
    return GuestSummarySchema.model_validate(row) if row else None


async def load_design_brief(session: AsyncSession, event_id: str) -> DesignBriefSchema | None:
    result = await session.execute(
        select(DesignBrief).where(DesignBrief.event_id == event_id)
    )
    row = result.scalar_one_or_none()
    return DesignBriefSchema.model_validate(row) if row else None


async def load_timeline_draft(session: AsyncSession, event_id: str) -> TimelineDraftSchema | None:
    result = await session.execute(
        select(TimelineDraft).where(TimelineDraft.event_id == event_id)
    )
    row = result.scalar_one_or_none()
    return TimelineDraftSchema.model_validate(row) if row else None


async def load_timeline_items(
    session: AsyncSession, event_id: str
) -> list[TimelineItemSchema]:
    stmt = (
        select(TimelineItem)
        .where(TimelineItem.event_id == event_id)
        .order_by(TimelineItem.sort_order.asc(), TimelineItem.time.asc())
    )
    result = await session.execute(stmt)
    return [TimelineItemSchema.model_validate(r) for r in result.scalars().all()]


async def load_files(
    session: AsyncSession,
    event_id: str,
    unreviewed_only: bool = False,
) -> list[FileRecordSchema]:
    stmt = select(FileRecord).where(FileRecord.event_id == event_id)
    if unreviewed_only:
        stmt = stmt.where(FileRecord.lead_reviewed.is_(False))
    stmt = stmt.order_by(FileRecord.uploaded_at.desc())
    result = await session.execute(stmt)
    return [FileRecordSchema.model_validate(r) for r in result.scalars().all()]


async def load_working_notes(
    session: AsyncSession, event_id: str
) -> WorkingNotesSchema | None:
    result = await session.execute(
        select(WorkingNotes).where(WorkingNotes.event_id == event_id)
    )
    row = result.scalar_one_or_none()
    return WorkingNotesSchema.model_validate(row) if row else None
