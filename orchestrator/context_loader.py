from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from memory import reader, summary as mem_summary

# Maps domain names to the extra memory sections they require beyond baseline.
# Baseline is always loaded: event_core, client_profile, recent_decisions,
# open_issues, and context_summary (working_notes).
_DOMAIN_TO_SECTIONS: dict[str, list[str]] = {
    "general":       [],
    "budget":        ["vendors", "budget"],
    "vendors":       ["vendors", "budget"],
    "timeline":      ["timeline"],
    "space":         ["timeline"],          # space needs timeline to check conflicts
    "guests":        ["guest_summary"],
    "design":        ["design_brief"],
    "entertainment": ["timeline"],
}


@dataclass
class LoadedContext:
    event_core: str
    client_profile: str
    recent_decisions: str
    open_issues: str
    context_summary: str
    vendors: str | None = None
    budget: str | None = None
    guest_summary: str | None = None
    design_brief: str | None = None
    timeline: str | None = None
    files_pending: str | None = None


async def load_baseline(session: AsyncSession, event_id: str) -> LoadedContext:
    """Load sections that are always included in every agent context."""
    event = await reader.load_event_core(session, event_id)
    profile = await reader.load_client_profile(session, event_id)
    recent_decisions = await reader.load_recent_decisions(session, event_id, limit=5)
    open_issues = await reader.load_open_issues(session, event_id)
    working_notes = await reader.load_working_notes(session, event_id)

    return LoadedContext(
        event_core=mem_summary.serialize_event_core(event) if event else "Event not found.",
        client_profile=mem_summary.serialize_client_profile(profile) if profile else "No client profile.",
        recent_decisions=mem_summary.serialize_confirmed_decisions(recent_decisions),
        open_issues=mem_summary.serialize_open_issues(open_issues),
        context_summary=mem_summary.serialize_working_notes(working_notes) if working_notes else "No summary.",
    )


async def load_for_domains(
    session: AsyncSession,
    event_id: str,
    domains: list[str],
) -> LoadedContext:
    """Load baseline plus any extra sections required by the given domains."""
    context = await load_baseline(session, event_id)

    # Collect which extra sections are needed, deduplicated
    needed: set[str] = set()
    for domain in domains:
        needed.update(_DOMAIN_TO_SECTIONS.get(domain, []))

    if "vendors" in needed:
        vendors = await reader.load_vendors(session, event_id)
        context.vendors = mem_summary.serialize_vendors(vendors)

    if "budget" in needed:
        budget = await reader.load_budget_summary(session, event_id)
        context.budget = mem_summary.serialize_budget_summary(budget) if budget else "No budget data."

    if "guest_summary" in needed:
        guests = await reader.load_guest_summary(session, event_id)
        context.guest_summary = mem_summary.serialize_guest_summary(guests) if guests else "No guest data."

    if "design_brief" in needed:
        brief = await reader.load_design_brief(session, event_id)
        context.design_brief = mem_summary.serialize_design_brief(brief) if brief else "No design brief."

    if "timeline" in needed:
        draft = await reader.load_timeline_draft(session, event_id)
        items = await reader.load_timeline_items(session, event_id)
        context.timeline = (
            mem_summary.serialize_timeline(draft, items) if draft else "No timeline draft."
        )

    # Always check for unreviewed files; include if any exist
    unreviewed_files = await reader.load_files(session, event_id, unreviewed_only=True)
    if unreviewed_files:
        context.files_pending = mem_summary.serialize_files(unreviewed_files)

    return context


def to_prompt_string(context: LoadedContext) -> str:
    """Assemble all loaded sections into a single prompt-ready string."""
    sections = [
        context.event_core,
        context.client_profile,
        context.recent_decisions,
        context.open_issues,
        context.context_summary,
    ]

    optional = [
        context.vendors,
        context.budget,
        context.guest_summary,
        context.design_brief,
        context.timeline,
        context.files_pending,
    ]
    sections.extend(s for s in optional if s is not None)

    return "\n\n".join(sections)
