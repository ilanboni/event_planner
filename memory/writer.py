from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    BudgetSummary, ClientProfile, ConfirmedDecision, DesignBrief,
    FileRecord, GuestSummary, OpenIssue, TimelineDraft,
    TimelineItem, Vendor, WorkingNotes,
)
from memory.schema import (
    BudgetSummarySchema, ClientProfileSchema, ConfirmedDecisionSchema,
    DesignBriefSchema, FileRecordSchema, GuestSummarySchema, OpenIssueSchema,
    TimelineDraftSchema, TimelineItemSchema, VendorSchema, WorkingNotesSchema,
)

_NOW = datetime.utcnow


# ── Decisions ─────────────────────────────────────────────────────────────────

async def write_confirmed_decision(
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
    if supersedes_id:
        old = await session.get(ConfirmedDecision, supersedes_id)
        if old:
            old.is_active = False
            session.add(old)

    decision = ConfirmedDecision(
        event_id=event_id,
        domain=domain,
        title=title,
        description=description,
        source=source,
        decided_by=decided_by,
        supersedes_id=supersedes_id,
        is_active=True,
        notes=notes,
    )
    session.add(decision)
    await session.commit()
    await session.refresh(decision)
    return ConfirmedDecisionSchema.model_validate(decision)


# ── Issues ────────────────────────────────────────────────────────────────────

async def create_open_issue(
    session: AsyncSession,
    event_id: str,
    domain: str,
    title: str,
    description: str,
    priority: str,
    created_by: str,
) -> OpenIssueSchema:
    issue = OpenIssue(
        event_id=event_id,
        domain=domain,
        title=title,
        description=description,
        priority=priority,
        status="open",
        created_by=created_by,
        issue_notes=[],
    )
    session.add(issue)
    await session.commit()
    await session.refresh(issue)
    return OpenIssueSchema.model_validate(issue)


async def update_issue_status(
    session: AsyncSession,
    issue_id: str,
    status: str,
    note_text: str | None = None,
) -> OpenIssueSchema:
    issue = await session.get(OpenIssue, issue_id)
    if issue is None:
        raise ValueError(f"Issue {issue_id} not found")

    issue.status = status
    issue.updated_at = _NOW()

    if note_text:
        existing_notes = list(issue.issue_notes or [])
        existing_notes.append({"text": note_text, "recorded_at": _NOW().isoformat()})
        issue.issue_notes = existing_notes

    session.add(issue)
    await session.commit()
    await session.refresh(issue)
    return OpenIssueSchema.model_validate(issue)


async def resolve_issue(
    session: AsyncSession,
    issue_id: str,
    decision_id: str,
) -> OpenIssueSchema:
    issue = await session.get(OpenIssue, issue_id)
    if issue is None:
        raise ValueError(f"Issue {issue_id} not found")

    issue.status = "resolved"
    issue.resolved_by_decision_id = decision_id
    issue.updated_at = _NOW()
    session.add(issue)
    await session.commit()
    await session.refresh(issue)
    return OpenIssueSchema.model_validate(issue)


# ── Client profile ────────────────────────────────────────────────────────────

async def append_raw_note(
    session: AsyncSession,
    event_id: str,
    text: str,
    source: str,
) -> ClientProfileSchema:
    result = await session.execute(
        select(ClientProfile).where(ClientProfile.event_id == event_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise ValueError(f"ClientProfile for event {event_id} not found")

    new_notes = list(profile.raw_notes or [])
    new_notes.append({
        "text": text,
        "recorded_at": _NOW().isoformat(),
        "source": source,
        "processed": False,
    })
    profile.raw_notes = new_notes
    profile.updated_at = _NOW()
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return ClientProfileSchema.model_validate(profile)


async def update_client_profile_fields(
    session: AsyncSession,
    event_id: str,
    **fields,
) -> ClientProfileSchema:
    result = await session.execute(
        select(ClientProfile).where(ClientProfile.event_id == event_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise ValueError(f"ClientProfile for event {event_id} not found")

    allowed = {
        "priorities", "hard_constraints", "soft_constraints",
        "style_preferences", "stated_concerns", "emotional_priorities",
    }
    for key, value in fields.items():
        if key in allowed:
            setattr(profile, key, value)

    profile.updated_at = _NOW()
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return ClientProfileSchema.model_validate(profile)


# ── Working notes ─────────────────────────────────────────────────────────────

async def update_working_notes_summary(
    session: AsyncSession,
    event_id: str,
    summary: str,
) -> WorkingNotesSchema:
    result = await session.execute(
        select(WorkingNotes).where(WorkingNotes.event_id == event_id)
    )
    notes = result.scalar_one_or_none()
    if notes is None:
        raise ValueError(f"WorkingNotes for event {event_id} not found")

    notes.lead_context_summary = summary
    notes.updated_at = _NOW()
    session.add(notes)
    await session.commit()
    await session.refresh(notes)
    return WorkingNotesSchema.model_validate(notes)


# ── Vendors ───────────────────────────────────────────────────────────────────

async def add_vendor(
    session: AsyncSession,
    event_id: str,
    name: str,
    category: str,
    notes: str | None = None,
) -> VendorSchema:
    vendor = Vendor(
        event_id=event_id,
        name=name,
        category=category,
        status="considering",
        notes=notes,
        linked_file_ids=[],
    )
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)
    return VendorSchema.model_validate(vendor)


async def update_vendor_fields(
    session: AsyncSession,
    vendor_id: str,
    **fields,
) -> VendorSchema:
    vendor = await session.get(Vendor, vendor_id)
    if vendor is None:
        raise ValueError(f"Vendor {vendor_id} not found")

    allowed = {
        "name", "category", "status", "quoted_cost",
        "confirmed_cost", "notes", "linked_file_ids",
    }
    for key, value in fields.items():
        if key in allowed:
            setattr(vendor, key, value)

    vendor.updated_at = _NOW()
    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)
    return VendorSchema.model_validate(vendor)


# ── Budget ────────────────────────────────────────────────────────────────────

async def update_budget_summary(
    session: AsyncSession,
    event_id: str,
    **fields,
) -> BudgetSummarySchema:
    result = await session.execute(
        select(BudgetSummary).where(BudgetSummary.event_id == event_id)
    )
    budget = result.scalar_one_or_none()
    if budget is None:
        raise ValueError(f"BudgetSummary for event {event_id} not found")

    allowed = {
        "total_ceiling", "total_committed", "total_estimated",
        "budget_status", "alerts",
    }
    for key, value in fields.items():
        if key in allowed:
            setattr(budget, key, value)

    budget.updated_at = _NOW()
    session.add(budget)
    await session.commit()
    await session.refresh(budget)
    return BudgetSummarySchema.model_validate(budget)


# ── Guest summary ─────────────────────────────────────────────────────────────

async def update_guest_summary(
    session: AsyncSession,
    event_id: str,
    **fields,
) -> GuestSummarySchema:
    result = await session.execute(
        select(GuestSummary).where(GuestSummary.event_id == event_id)
    )
    guests = result.scalar_one_or_none()
    if guests is None:
        raise ValueError(f"GuestSummary for event {event_id} not found")

    allowed = {
        "total_invited", "adults_count", "children_count",
        "dietary_restrictions", "accessibility_needs",
        "vip_guests", "seating_status", "hospitality_notes",
    }
    for key, value in fields.items():
        if key in allowed:
            setattr(guests, key, value)

    guests.updated_at = _NOW()
    session.add(guests)
    await session.commit()
    await session.refresh(guests)
    return GuestSummarySchema.model_validate(guests)


# ── Design brief ──────────────────────────────────────────────────────────────

async def update_design_brief(
    session: AsyncSession,
    event_id: str,
    **fields,
) -> DesignBriefSchema:
    result = await session.execute(
        select(DesignBrief).where(DesignBrief.event_id == event_id)
    )
    brief = result.scalar_one_or_none()
    if brief is None:
        raise ValueError(f"DesignBrief for event {event_id} not found")

    allowed = {
        "theme_name", "theme_description", "color_palette",
        "color_palette_confirmed", "style_keywords",
        "confirmed_elements", "open_elements", "reference_file_ids",
    }
    for key, value in fields.items():
        if key in allowed:
            setattr(brief, key, value)

    brief.updated_at = _NOW()
    session.add(brief)
    await session.commit()
    await session.refresh(brief)
    return DesignBriefSchema.model_validate(brief)


# ── Timeline ──────────────────────────────────────────────────────────────────

async def update_timeline_draft(
    session: AsyncSession,
    event_id: str,
    **fields,
) -> TimelineDraftSchema:
    result = await session.execute(
        select(TimelineDraft).where(TimelineDraft.event_id == event_id)
    )
    draft = result.scalar_one_or_none()
    if draft is None:
        raise ValueError(f"TimelineDraft for event {event_id} not found")

    allowed = {
        "status", "setup_start", "setup_end",
        "doors_open", "event_end_estimated", "open_timing_issues",
    }
    for key, value in fields.items():
        if key in allowed:
            setattr(draft, key, value)

    draft.updated_at = _NOW()
    session.add(draft)
    await session.commit()
    await session.refresh(draft)
    return TimelineDraftSchema.model_validate(draft)


async def add_timeline_item(
    session: AsyncSession,
    event_id: str,
    time: str,
    label: str,
    duration_minutes: int | None = None,
    location_in_venue: str | None = None,
    owner: str | None = None,
    notes: str | None = None,
    sort_order: int = 0,
) -> TimelineItemSchema:
    item = TimelineItem(
        event_id=event_id,
        time=time,
        label=label,
        duration_minutes=duration_minutes,
        location_in_venue=location_in_venue,
        owner=owner,
        notes=notes,
        sort_order=sort_order,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return TimelineItemSchema.model_validate(item)


# ── Files ─────────────────────────────────────────────────────────────────────

async def create_file_record(
    session: AsyncSession,
    event_id: str,
    original_filename: str,
    storage_path: str,
    file_type: str = "other",
) -> FileRecordSchema:
    record = FileRecord(
        event_id=event_id,
        original_filename=original_filename,
        storage_path=storage_path,
        file_type=file_type,
        processed=False,
        lead_reviewed=False,
        linked_domains=[],
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return FileRecordSchema.model_validate(record)


async def mark_file_processed(
    session: AsyncSession,
    file_id: str,
    summary: str,
    extracted_data: dict,
    linked_domains: list[str],
) -> FileRecordSchema:
    record = await session.get(FileRecord, file_id)
    if record is None:
        raise ValueError(f"FileRecord {file_id} not found")

    record.processed = True
    record.summary = summary
    record.extracted_data = extracted_data
    record.linked_domains = linked_domains
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return FileRecordSchema.model_validate(record)


async def mark_file_lead_reviewed(
    session: AsyncSession,
    file_id: str,
    action_taken: str,
) -> FileRecordSchema:
    record = await session.get(FileRecord, file_id)
    if record is None:
        raise ValueError(f"FileRecord {file_id} not found")

    record.lead_reviewed = True
    record.lead_action_taken = action_taken
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return FileRecordSchema.model_validate(record)
