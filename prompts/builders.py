from __future__ import annotations

import json

from orchestrator.context_loader import LoadedContext, to_prompt_string


def build_lead_classification_message(
    context: LoadedContext,
    message_text: str,
) -> str:
    """
    User-turn message for the Lead Agent's classification call.
    Includes only the baseline context (event core, profile, recent decisions,
    open issues, context summary) to keep the routing call fast and cheap.
    """
    baseline = "\n\n".join(filter(None, [
        context.event_core,
        context.client_profile,
        context.recent_decisions,
        context.open_issues,
        context.context_summary,
    ]))

    return (
        f"CURRENT EVENT MEMORY:\n{baseline}\n\n"
        f"CLIENT MESSAGE:\n{message_text or '(no text — attachment only)'}\n\n"
        "Return your routing decision as a JSON object."
    )


def build_lead_synthesis_message(
    context: LoadedContext,
    message_text: str,
    archivist_output: dict | None = None,
    recent_messages: list[str] | None = None,
) -> str:
    """
    User-turn message for the Lead Agent's synthesis call.
    Includes the full loaded context, optional archivist extraction,
    and recent conversation history for continuity.
    """
    parts: list[str] = []

    parts.append(f"FULL EVENT MEMORY:\n{to_prompt_string(context)}")

    if recent_messages:
        history = "\n".join(recent_messages)
        parts.append(f"RECENT CONVERSATION (oldest first):\n{history}")

    if archivist_output:
        parts.append(
            f"ARCHIVIST FILE ANALYSIS:\n{json.dumps(archivist_output, indent=2, ensure_ascii=False)}"
        )

    parts.append(f"CLIENT MESSAGE:\n{message_text or '(no text — see file analysis above)'}")
    parts.append("Return your response as a JSON object.")

    return "\n\n".join(parts)


def build_specialist_message(
    context: LoadedContext,
    message_text: str,
    domain: str,
    archivist_output: dict | None = None,
) -> str:
    """
    User-turn message for specialist agents (Phase 5+).
    Includes only the sections relevant to the specialist's domain.
    """
    domain_section_map: dict[str, list[str]] = {
        "budget":        [context.vendors, context.budget],
        "vendors":       [context.vendors, context.budget],
        "timeline":      [context.timeline],
        "space":         [context.timeline],
        "guests":        [context.guest_summary],
        "design":        [context.design_brief],
        "entertainment": [context.timeline],
    }

    relevant = [context.event_core, context.client_profile]
    relevant += [s for s in domain_section_map.get(domain, []) if s]

    parts: list[str] = [f"RELEVANT EVENT MEMORY:\n{chr(10).join(relevant)}"]

    if archivist_output:
        parts.append(
            f"ARCHIVIST FILE ANALYSIS:\n{json.dumps(archivist_output, indent=2, ensure_ascii=False)}"
        )

    parts.append(f"CLIENT MESSAGE:\n{message_text}")
    parts.append("Return your domain analysis as a JSON object.")

    return "\n\n".join(parts)
