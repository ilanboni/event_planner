from __future__ import annotations

import re
from dataclasses import dataclass, field

from bot.message_handler import IncomingMessage

# ── Keyword sets for deterministic routing ────────────────────────────────────

_BUDGET_KEYWORDS = re.compile(
    r"\b(cost|costs|price|pricing|quote|quotation|invoice|invoic|budget|payment|pay|"
    r"deposit|fee|fees|spend|spending|afford|preventivo|offerta|devis|costo|prezzo|"
    r"€|\$|£)\b",
    re.IGNORECASE,
)

_TIMELINE_KEYWORDS = re.compile(
    r"\b(time|timing|schedule|scheduled|when|start|end|ceremony|arrival|arrive|"
    r"run.of.show|runofshow|program|programme|duration|order.of.events|hora|"
    r"orario|programma|ablauf)\b",
    re.IGNORECASE,
)

_SPACE_KEYWORDS = re.compile(
    r"\b(floor.?plan|layout|table|tables|seating|seat|room|venue.map|placement|"
    r"entrance|exit|capacity|fit|fits|space|setup|set.up|stage|dance.floor|"
    r"planimetria|pianta|disposizione)\b",
    re.IGNORECASE,
)

_GUEST_KEYWORDS = re.compile(
    r"\b(guest|guests|rsvp|dietary|allerg|vegeta|vegan|kosher|gluten|"
    r"attendance|invite|invit|headcount|family|ospiti|invitati)\b",
    re.IGNORECASE,
)

_DESIGN_KEYWORDS = re.compile(
    r"\b(color|colour|palette|theme|décor|decor|flower|floral|lighting|light|"
    r"style|aesthetic|mood.?board|inspiration|table.?setting|centrepiece|centerpiece|"
    r"colore|fiori|allestimento|decorazion)\b",
    re.IGNORECASE,
)

_ENTERTAINMENT_KEYWORDS = re.compile(
    r"\b(dj|band|music|song|playlist|activity|activities|game|games|kids?|children|"
    r"candle.?light|speech|speeches|toast|performance|entertai|musica|bambini)\b",
    re.IGNORECASE,
)


@dataclass
class RouterResult:
    domains_involved: list[str] = field(default_factory=list)
    routing_method: str = "deterministic"    # deterministic | lead_agent
    is_attachment_only: bool = False


def route(message: IncomingMessage) -> RouterResult:
    """
    Deterministic pre-classification.

    Rules (in order of specificity):
      1. Attachment with no text → is_attachment_only, Lead handles after Archivist
      2. Single clear domain match → deterministic routing
      3. Multiple domain matches or no match → defer to Lead Agent classification

    The router does NOT call the Lead Agent — it returns a RouterResult that tells
    the pipeline whether to proceed deterministically or hand off to classification.
    """
    text = (message.text or "").strip()

    if not text and message.attachments:
        return RouterResult(domains_involved=[], routing_method="lead_agent", is_attachment_only=True)

    matched: list[str] = []

    if _BUDGET_KEYWORDS.search(text):
        matched.append("budget")
    if _TIMELINE_KEYWORDS.search(text):
        matched.append("timeline")
    if _SPACE_KEYWORDS.search(text):
        matched.append("space")
    if _GUEST_KEYWORDS.search(text):
        matched.append("guests")
    if _DESIGN_KEYWORDS.search(text):
        matched.append("design")
    if _ENTERTAINMENT_KEYWORDS.search(text):
        matched.append("entertainment")

    if len(matched) == 1:
        # Clear single-domain message — route deterministically
        return RouterResult(domains_involved=matched, routing_method="deterministic")

    if len(matched) >= 2:
        # Cross-domain — Lead Agent classifies and may invoke multiple specialists
        return RouterResult(domains_involved=matched, routing_method="lead_agent")

    # No keyword match — general or conversational message, Lead Agent handles
    return RouterResult(domains_involved=[], routing_method="lead_agent")
