from __future__ import annotations

from memory.schema import (
    BudgetSummarySchema, ClientProfileSchema, ConfirmedDecisionSchema,
    DesignBriefSchema, EventCoreSchema, FileRecordSchema, GuestSummarySchema,
    OpenIssueSchema, TimelineDraftSchema, TimelineItemSchema, WorkingNotesSchema,
)

_NONE = "None recorded."


def serialize_event_core(event: EventCoreSchema) -> str:
    venue_status = "[BOOKED]" if event.venue_booked else "[NOT CONFIRMED]"
    time_range = event.event_time_start or "TBD"
    if event.event_time_end_estimated:
        time_range += f"–{event.event_time_end_estimated}"
    guests = str(event.guest_count_estimated or "TBD")
    if event.guest_count_confirmed:
        guests += f" ({event.guest_count_confirmed} confirmed)"

    lines = [
        "=== EVENT CORE ===",
        f"Event:    {event.event_name}",
        f"Honoree:  {event.honoree_name or 'TBD'}",
        f"Client:   {event.client_name}",
        f"Date:     {event.event_date or 'TBD'}  |  Time: {time_range}",
        f"Type:     {event.ceremony_type or 'TBD'}",
        f"Venue:    {event.venue_name or 'TBD'} {venue_status}",
    ]
    if event.venue_address:
        lines.append(f"Address:  {event.venue_address}")
    lines.append(f"Guests:   ~{guests} estimated")
    return "\n".join(lines)


def serialize_client_profile(profile: ClientProfileSchema) -> str:
    lines = ["=== CLIENT PROFILE ==="]

    if profile.priorities:
        lines.append("Priorities:")
        for i, p in enumerate(profile.priorities, 1):
            lines.append(f"  {i}. {p}")

    if profile.emotional_priorities:
        lines.append("Emotional priorities:")
        for ep in profile.emotional_priorities:
            lines.append(f"  • {ep}")

    if profile.hard_constraints:
        lines.append("Hard constraints:")
        for c in profile.hard_constraints:
            lines.append(f"  ✗ {c.description}")

    if profile.soft_constraints:
        lines.append("Soft constraints:")
        for c in profile.soft_constraints:
            lines.append(f"  ~ {c.description}")

    if profile.style_preferences:
        lines.append(f"Style: {', '.join(profile.style_preferences)}")

    if profile.stated_concerns:
        open_concerns = [c for c in profile.stated_concerns if not c.resolved]
        if open_concerns:
            lines.append("Open concerns:")
            for c in open_concerns:
                lines.append(f"  ⚠ {c.topic}: {c.description}")

    # Only unprocessed raw notes, capped at 5 most recent
    unprocessed = [n for n in profile.raw_notes if not n.processed][-5:]
    if unprocessed:
        lines.append("Recent unprocessed notes:")
        for n in unprocessed:
            lines.append(f"  [{n.source}] {n.text}")

    if len(lines) == 1:
        lines.append(_NONE)
    return "\n".join(lines)


def serialize_confirmed_decisions(decisions: list[ConfirmedDecisionSchema]) -> str:
    if not decisions:
        return "=== CONFIRMED DECISIONS ===\n" + _NONE

    by_domain: dict[str, list[ConfirmedDecisionSchema]] = {}
    for d in decisions:
        by_domain.setdefault(d.domain, []).append(d)

    lines = ["=== CONFIRMED DECISIONS ==="]
    for domain, items in sorted(by_domain.items()):
        lines.append(f"\n[{domain.upper()}]")
        for d in items:
            date_str = d.created_at.strftime("%Y-%m-%d") if d.created_at else "?"
            lines.append(f"  [{date_str}] {d.title}")
            lines.append(f"    {d.description}")
            lines.append(f"    decided_by: {d.decided_by} | source: {d.source}")
    return "\n".join(lines)


def serialize_open_issues(issues: list[OpenIssueSchema]) -> str:
    if not issues:
        return "=== OPEN ISSUES ===\nNo open issues."

    lines = ["=== OPEN ISSUES ==="]
    for i in issues:
        awaiting = f" | awaiting: {i.awaiting_input_from}" if i.awaiting_input_from else ""
        lines.append(
            f"  [{i.priority.upper()}] {i.title} ({i.domain}) | {i.status}{awaiting}"
        )
        lines.append(f"    {i.description}")
    return "\n".join(lines)


def serialize_vendors(vendors: list[VendorSchema]) -> str:
    if not vendors:
        return "=== VENDORS ===\n" + _NONE

    by_status: dict[str, list[VendorSchema]] = {}
    for v in vendors:
        by_status.setdefault(v.status, []).append(v)

    status_order = ["confirmed", "pending_approval", "quote_received", "considering", "rejected", "cancelled"]
    lines = ["=== VENDORS ==="]
    for status in status_order:
        items = by_status.get(status, [])
        if not items:
            continue
        lines.append(f"\n[{status.upper().replace('_', ' ')}]")
        for v in items:
            cost_parts = []
            if v.confirmed_cost is not None:
                cost_parts.append(f"confirmed: €{v.confirmed_cost:,.0f}")
            if v.quoted_cost is not None and v.confirmed_cost is None:
                cost_parts.append(f"quoted: €{v.quoted_cost:,.0f}")
            cost_str = f" | {', '.join(cost_parts)}" if cost_parts else ""
            note_str = f" | {v.notes}" if v.notes else ""
            lines.append(f"  {v.name} ({v.category}){cost_str}{note_str}")
    return "\n".join(lines)


def serialize_budget_summary(budget: BudgetSummarySchema) -> str:
    lines = ["=== BUDGET ==="]
    ceiling = f"€{budget.total_ceiling:,.0f}" if budget.total_ceiling else "not set"
    lines.append(f"Ceiling:    {ceiling}")
    lines.append(f"Committed:  €{budget.total_committed:,.0f}")
    lines.append(f"Estimated:  €{budget.total_estimated:,.0f}")
    lines.append(f"Status:     {budget.budget_status.upper()}")

    unacknowledged = [a for a in budget.alerts if not a.acknowledged]
    if unacknowledged:
        lines.append("Alerts:")
        for alert in unacknowledged:
            lines.append(f"  ⚠ [{alert.type}] {alert.message}")
    return "\n".join(lines)


def serialize_guest_summary(guests: GuestSummarySchema) -> str:
    lines = ["=== GUESTS ==="]
    total = guests.total_invited or "TBD"
    adults = guests.adults_count or "?"
    children = guests.children_count or "?"
    lines.append(f"Total invited: {total}  (adults: {adults}, children: {children})")
    lines.append(f"Seating status: {guests.seating_status}")

    if guests.dietary_restrictions:
        diet_parts = [f"{k}: {v}" for k, v in guests.dietary_restrictions.items()]
        lines.append(f"Dietary: {', '.join(diet_parts)}")

    if guests.accessibility_needs:
        lines.append("Accessibility:")
        for need in guests.accessibility_needs:
            lines.append(f"  • {need}")

    if guests.vip_guests:
        lines.append("VIP guests:")
        for vip in guests.vip_guests:
            note = f" — {vip.special_handling_notes}" if vip.special_handling_notes else ""
            lines.append(f"  ★ {vip.name} ({vip.relationship}){note}")

    if guests.hospitality_notes:
        lines.append(f"Notes: {guests.hospitality_notes}")
    return "\n".join(lines)


def serialize_design_brief(brief: DesignBriefSchema) -> str:
    lines = ["=== DESIGN BRIEF ==="]

    theme = brief.theme_name or "Not defined"
    lines.append(f"Theme: {theme}")
    if brief.theme_description:
        lines.append(f"  {brief.theme_description}")

    if brief.color_palette:
        confirmed = " [CONFIRMED]" if brief.color_palette_confirmed else ""
        lines.append(f"Palette{confirmed}: {', '.join(brief.color_palette)}")

    if brief.style_keywords:
        lines.append(f"Style: {', '.join(brief.style_keywords)}")

    confirmed_els = [e for e in brief.confirmed_elements if e.status == "confirmed"]
    if confirmed_els:
        lines.append("Confirmed elements:")
        for el in confirmed_els:
            lines.append(f"  ✓ {el.element}: {el.description}")

    if brief.open_elements:
        lines.append("Open elements:")
        for el in brief.open_elements:
            lines.append(f"  ○ {el}")

    if len(lines) == 1:
        lines.append(_NONE)
    return "\n".join(lines)


def serialize_timeline(
    draft: TimelineDraftSchema,
    items: list[TimelineItemSchema],
) -> str:
    lines = ["=== TIMELINE ==="]
    lines.append(f"Status: {draft.status}")

    if draft.setup_start or draft.setup_end:
        lines.append(f"Setup: {draft.setup_start or '?'} – {draft.setup_end or '?'}")
    if draft.doors_open:
        lines.append(f"Doors open: {draft.doors_open}")
    if draft.event_end_estimated:
        lines.append(f"Est. end: {draft.event_end_estimated}")

    if items:
        lines.append("\nSchedule:")
        for item in items:
            dur = f" ({item.duration_minutes}min)" if item.duration_minutes else ""
            loc = f" @ {item.location_in_venue}" if item.location_in_venue else ""
            lines.append(f"  {item.time}{dur}  {item.label}{loc}")
            if item.notes:
                lines.append(f"    → {item.notes}")
    else:
        lines.append("Schedule: not yet built")

    if draft.open_timing_issues:
        lines.append("Timing issues:")
        for issue in draft.open_timing_issues:
            lines.append(f"  ⚠ {issue}")
    return "\n".join(lines)


def serialize_files(files: list[FileRecordSchema]) -> str:
    processed = [f for f in files if f.processed]
    if not processed:
        return "=== FILES ===\nNo processed files."

    lines = ["=== FILES ==="]
    for f in processed:
        reviewed = "reviewed" if f.lead_reviewed else "PENDING LEAD REVIEW"
        lines.append(f"  [{f.file_type}] {f.original_filename} | {reviewed}")
        if f.summary:
            lines.append(f"    {f.summary}")
    return "\n".join(lines)


def serialize_working_notes(notes: WorkingNotesSchema) -> str:
    if not notes.lead_context_summary:
        return "=== CONTEXT SUMMARY ===\nNo summary recorded yet."
    return f"=== CONTEXT SUMMARY ===\n{notes.lead_context_summary}"
