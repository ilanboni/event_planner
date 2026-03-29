from __future__ import annotations

import json
from dataclasses import dataclass, field

from agents.base import BaseAgent
from prompts.timeline_agent import TIMELINE_SYSTEM_PROMPT
from utils.logger import logger


# ── Output dataclass ──────────────────────────────────────────────────────────

@dataclass
class TimelineAnalysis:
    """
    Structured pacing and sequencing briefing produced by the Timeline Agent.
    Passed to the Lead Agent as part of specialist_outputs; never sent to
    the client.

    Fields:
      assessment    — current timeline status in plain language
      pacing_notes  — qualitative observations about specific time ranges
      conflicts     — hard timing problems (overlaps, impossible transitions)
      flags         — risks and missing information
      recommendation — one clear direction for the Lead Agent to act on
    """
    assessment: str
    pacing_notes: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    recommendation: str = ""
    proposed_decisions: list[dict] = field(default_factory=list)
    proposed_issues: list[dict] = field(default_factory=list)
    clarification_needed: bool = False
    clarification_question: str | None = None

    def to_dict(self) -> dict:
        return {
            "assessment": self.assessment,
            "pacing_notes": self.pacing_notes,
            "conflicts": self.conflicts,
            "flags": self.flags,
            "recommendation": self.recommendation,
            "proposed_decisions": self.proposed_decisions,
            "proposed_issues": self.proposed_issues,
            "clarification_needed": self.clarification_needed,
            "clarification_question": self.clarification_question,
        }

    @classmethod
    def fallback(cls) -> TimelineAnalysis:
        return cls(
            assessment="Timeline analysis unavailable — check logs.",
            flags=["Timeline Agent failed to run — pacing context not available."],
            recommendation="",
        )


# ── Agent ─────────────────────────────────────────────────────────────────────

class TimelineAgent(BaseAgent):
    """
    Internal event pacing and sequencing specialist.

    Receives the serialized event context (event core, timeline draft, schedule
    items) and the client message. Returns a TimelineAnalysis that the Lead
    Agent uses when composing the final response and deciding which memory
    writes to execute.

    Never raises — falls back to TimelineAnalysis.fallback().
    """

    async def analyze(
        self,
        message_text: str,
        timeline_context: str,
    ) -> TimelineAnalysis:
        user_message = (
            f"EVENT AND TIMELINE CONTEXT:\n{timeline_context}\n\n"
            f"CLIENT MESSAGE:\n{message_text or '(no text)'}\n\n"
            "Return your timeline analysis as a JSON object."
        )

        try:
            raw = await self._call_llm(
                system_prompt=TIMELINE_SYSTEM_PROMPT,
                user_message=user_message,
                json_mode=True,
                temperature=0.2,
            )
            return _parse_timeline_analysis(raw)
        except Exception as exc:
            logger.warning("Timeline Agent analysis failed: %s", exc)
            return TimelineAnalysis.fallback()


# ── Parser ────────────────────────────────────────────────────────────────────

def _parse_timeline_analysis(raw: str) -> TimelineAnalysis:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Timeline analysis JSON parse error: {exc}") from exc

    return TimelineAnalysis(
        assessment=data.get("assessment", ""),
        pacing_notes=_coerce_str_list(data.get("pacing_notes")),
        conflicts=_coerce_str_list(data.get("conflicts")),
        flags=_coerce_str_list(data.get("flags")),
        recommendation=data.get("recommendation", ""),
        proposed_decisions=_coerce_list_of_dicts(data.get("proposed_decisions")),
        proposed_issues=_coerce_list_of_dicts(data.get("proposed_issues")),
        clarification_needed=bool(data.get("clarification_needed", False)),
        clarification_question=data.get("clarification_question") or None,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _coerce_list_of_dicts(value) -> list[dict]:
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    return []


def _coerce_str_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    return []
