from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Nested objects for JSON fields ────────────────────────────────────────────

class ConstraintItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str = ""           # hard | soft
    description: str = ""
    source: str = ""
    recorded_at: str = ""


class ConcernItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    topic: str = ""
    description: str = ""
    recorded_at: str = ""
    resolved: bool = False


class RawNote(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    text: str = ""
    recorded_at: str = ""
    source: str = ""         # telegram_message | file_extraction | lead_observation
    processed: bool = False


class IssueNote(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    text: str = ""
    recorded_at: str = ""


class BudgetAlertSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str = ""
    message: str = ""
    domain: str = ""
    amount: float | None = None
    created_at: str = ""
    acknowledged: bool = False


class VipGuestSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str = ""
    relationship: str = ""
    special_handling_notes: str = ""


class DesignElementSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    element: str = ""
    description: str = ""
    status: str = "open"     # confirmed | in_progress | open
    notes: str = ""


# ── Main memory section schemas ───────────────────────────────────────────────

class EventCoreSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_name: str
    event_date: str | None = None
    event_time_start: str | None = None
    event_time_end_estimated: str | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    venue_booked: bool = True
    guest_count_estimated: int | None = None
    guest_count_confirmed: int | None = None
    client_name: str
    client_telegram_id: str
    honoree_name: str | None = None
    ceremony_type: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ClientProfileSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    priorities: list[str] = Field(default_factory=list)
    hard_constraints: list[ConstraintItem] = Field(default_factory=list)
    soft_constraints: list[ConstraintItem] = Field(default_factory=list)
    style_preferences: list[str] = Field(default_factory=list)
    stated_concerns: list[ConcernItem] = Field(default_factory=list)
    emotional_priorities: list[str] = Field(default_factory=list)
    raw_notes: list[RawNote] = Field(default_factory=list)
    updated_at: datetime | None = None


class ConfirmedDecisionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    domain: str
    title: str
    description: str
    source: str
    decided_by: str
    supersedes_id: str | None = None
    is_active: bool = True
    notes: str | None = None
    created_at: datetime | None = None


class OpenIssueSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    domain: str
    title: str
    description: str
    priority: str
    status: str
    created_by: str
    awaiting_input_from: str | None = None
    resolved_by_decision_id: str | None = None
    issue_notes: list[IssueNote] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class VendorSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    name: str
    category: str
    status: str
    quoted_cost: float | None = None
    confirmed_cost: float | None = None
    notes: str | None = None
    linked_file_ids: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class BudgetSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    total_ceiling: float | None = None
    total_committed: float = 0.0
    total_estimated: float = 0.0
    budget_status: str = "healthy"
    alerts: list[BudgetAlertSchema] = Field(default_factory=list)
    updated_at: datetime | None = None


class GuestSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    total_invited: int | None = None
    adults_count: int | None = None
    children_count: int | None = None
    dietary_restrictions: dict[str, Any] = Field(default_factory=dict)
    accessibility_needs: list[str] = Field(default_factory=list)
    vip_guests: list[VipGuestSchema] = Field(default_factory=list)
    seating_status: str = "not_started"
    hospitality_notes: str | None = None
    updated_at: datetime | None = None


class DesignBriefSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    theme_name: str | None = None
    theme_description: str | None = None
    color_palette: list[str] = Field(default_factory=list)
    color_palette_confirmed: bool = False
    style_keywords: list[str] = Field(default_factory=list)
    confirmed_elements: list[DesignElementSchema] = Field(default_factory=list)
    open_elements: list[str] = Field(default_factory=list)
    reference_file_ids: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None


class TimelineDraftSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    status: str = "not_started"
    setup_start: str | None = None
    setup_end: str | None = None
    doors_open: str | None = None
    event_end_estimated: str | None = None
    open_timing_issues: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None


class TimelineItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    time: str
    duration_minutes: int | None = None
    label: str
    location_in_venue: str | None = None
    owner: str | None = None
    notes: str | None = None
    sort_order: int = 0


class FileRecordSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    original_filename: str
    file_type: str = "other"
    processed: bool = False
    summary: str | None = None
    extracted_data: dict[str, Any] | None = None
    linked_domains: list[str] = Field(default_factory=list)
    storage_path: str
    lead_reviewed: bool = False
    lead_action_taken: str | None = None
    uploaded_at: datetime | None = None


class WorkingNotesSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    lead_context_summary: str | None = None
    specialist_recommendations: list[dict] = Field(default_factory=list)
    archivist_pending_review: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None
