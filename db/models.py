import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase


def new_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, default=new_uuid)
    event_name = Column(String, nullable=False)
    event_date = Column(String, nullable=True)               # YYYY-MM-DD
    event_time_start = Column(String, nullable=True)         # HH:MM
    event_time_end_estimated = Column(String, nullable=True) # HH:MM
    venue_name = Column(String, nullable=True)
    venue_address = Column(String, nullable=True)
    venue_booked = Column(Boolean, default=True)
    guest_count_estimated = Column(Integer, nullable=True)
    guest_count_confirmed = Column(Integer, nullable=True)
    client_name = Column(String, nullable=False)
    client_telegram_id = Column(String, unique=True, nullable=False, index=True)
    honoree_name = Column(String, nullable=True)
    ceremony_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ClientProfile(Base):
    __tablename__ = "client_profile"
    __table_args__ = (UniqueConstraint("event_id"),)

    id = Column(String, primary_key=True, default=new_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    priorities = Column(JSON, default=list)
    hard_constraints = Column(JSON, default=list)
    soft_constraints = Column(JSON, default=list)
    style_preferences = Column(JSON, default=list)
    stated_concerns = Column(JSON, default=list)
    emotional_priorities = Column(JSON, default=list)
    raw_notes = Column(JSON, default=list)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConfirmedDecision(Base):
    __tablename__ = "confirmed_decisions"

    id = Column(String, primary_key=True, default=new_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=False, index=True)
    domain = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    source = Column(String, nullable=False)
    decided_by = Column(String, nullable=False)
    supersedes_id = Column(String, ForeignKey("confirmed_decisions.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class OpenIssue(Base):
    __tablename__ = "open_issues"

    id = Column(String, primary_key=True, default=new_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=False, index=True)
    domain = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String, nullable=False, default="medium")
    status = Column(String, nullable=False, default="open")
    created_by = Column(String, nullable=False)
    awaiting_input_from = Column(String, nullable=True)
    resolved_by_decision_id = Column(String, ForeignKey("confirmed_decisions.id"), nullable=True)
    issue_notes = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(String, primary_key=True, default=new_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    status = Column(String, nullable=False, default="considering")
    quoted_cost = Column(Float, nullable=True)
    confirmed_cost = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    linked_file_ids = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BudgetSummary(Base):
    __tablename__ = "budget_summary"
    __table_args__ = (UniqueConstraint("event_id"),)

    id = Column(String, primary_key=True, default=new_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    total_ceiling = Column(Float, nullable=True)
    total_committed = Column(Float, default=0.0)
    total_estimated = Column(Float, default=0.0)
    budget_status = Column(String, default="healthy")
    alerts = Column(JSON, default=list)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GuestSummary(Base):
    __tablename__ = "guest_summary"
    __table_args__ = (UniqueConstraint("event_id"),)

    id = Column(String, primary_key=True, default=new_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    total_invited = Column(Integer, nullable=True)
    adults_count = Column(Integer, nullable=True)
    children_count = Column(Integer, nullable=True)
    dietary_restrictions = Column(JSON, default=dict)
    accessibility_needs = Column(JSON, default=list)
    vip_guests = Column(JSON, default=list)
    seating_status = Column(String, default="not_started")
    hospitality_notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DesignBrief(Base):
    __tablename__ = "design_brief"
    __table_args__ = (UniqueConstraint("event_id"),)

    id = Column(String, primary_key=True, default=new_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    theme_name = Column(String, nullable=True)
    theme_description = Column(Text, nullable=True)
    color_palette = Column(JSON, default=list)
    color_palette_confirmed = Column(Boolean, default=False)
    style_keywords = Column(JSON, default=list)
    confirmed_elements = Column(JSON, default=list)
    open_elements = Column(JSON, default=list)
    reference_file_ids = Column(JSON, default=list)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TimelineDraft(Base):
    __tablename__ = "timeline_draft"
    __table_args__ = (UniqueConstraint("event_id"),)

    id = Column(String, primary_key=True, default=new_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    status = Column(String, default="not_started")
    setup_start = Column(String, nullable=True)          # HH:MM
    setup_end = Column(String, nullable=True)            # HH:MM
    doors_open = Column(String, nullable=True)           # HH:MM
    event_end_estimated = Column(String, nullable=True)  # HH:MM
    open_timing_issues = Column(JSON, default=list)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TimelineItem(Base):
    __tablename__ = "timeline_items"

    id = Column(String, primary_key=True, default=new_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=False, index=True)
    time = Column(String, nullable=False)                # HH:MM
    duration_minutes = Column(Integer, nullable=True)
    label = Column(String, nullable=False)
    location_in_venue = Column(String, nullable=True)
    owner = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    sort_order = Column(Integer, default=0)


class FileRecord(Base):
    __tablename__ = "files"

    id = Column(String, primary_key=True, default=new_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=False, index=True)
    original_filename = Column(String, nullable=False)
    file_type = Column(String, default="other")
    processed = Column(Boolean, default=False)
    summary = Column(Text, nullable=True)
    extracted_data = Column(JSON, nullable=True)
    linked_domains = Column(JSON, default=list)
    storage_path = Column(String, nullable=False)
    lead_reviewed = Column(Boolean, default=False)
    lead_action_taken = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)


class WorkingNotes(Base):
    __tablename__ = "working_notes"
    __table_args__ = (UniqueConstraint("event_id"),)

    id = Column(String, primary_key=True, default=new_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    lead_context_summary = Column(Text, nullable=True)
    specialist_recommendations = Column(JSON, default=list)
    archivist_pending_review = Column(JSON, default=list)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=new_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=True, index=True)
    telegram_message_id = Column(Integer, nullable=True)
    chat_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=True)
    direction = Column(String, nullable=False)  # incoming | outgoing
    text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
