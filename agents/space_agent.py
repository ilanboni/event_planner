from __future__ import annotations

import json
from dataclasses import dataclass, field

from agents.base import BaseAgent
from prompts.space_agent import SPACE_SYSTEM_PROMPT
from utils.logger import logger


# ── Output dataclass ──────────────────────────────────────────────────────────

@dataclass
class SpaceAnalysis:
    """
    Structured spatial briefing produced by the Space Agent.
    Passed to the Lead Agent as part of specialist_outputs; never sent to
    the client.
    """
    assessment: str
    flags: list[str] = field(default_factory=list)
    recommendation: str = ""
    proposed_decisions: list[dict] = field(default_factory=list)
    proposed_issues: list[dict] = field(default_factory=list)
    clarification_needed: bool = False
    clarification_question: str | None = None

    def to_dict(self) -> dict:
        return {
            "assessment": self.assessment,
            "flags": self.flags,
            "recommendation": self.recommendation,
            "proposed_decisions": self.proposed_decisions,
            "proposed_issues": self.proposed_issues,
            "clarification_needed": self.clarification_needed,
            "clarification_question": self.clarification_question,
        }

    @classmethod
    def fallback(cls) -> SpaceAnalysis:
        return cls(
            assessment="Spatial analysis unavailable — check logs.",
            flags=["Space Agent failed to run — spatial context not available."],
            recommendation="",
        )


# ── Agent ─────────────────────────────────────────────────────────────────────

class SpaceAgent(BaseAgent):
    """
    Internal spatial planning specialist.

    Receives the serialized event context (venue info, timeline, confirmed
    decisions) and the client message. Returns a SpaceAnalysis that the Lead
    Agent uses when composing the final response and deciding which memory
    writes to execute.

    Never raises — falls back to SpaceAnalysis.fallback().
    """

    async def analyze(
        self,
        message_text: str,
        space_context: str,
    ) -> SpaceAnalysis:
        user_message = (
            f"EVENT AND VENUE CONTEXT:\n{space_context}\n\n"
            f"CLIENT MESSAGE:\n{message_text or '(no text)'}\n\n"
            "Return your spatial analysis as a JSON object."
        )

        try:
            raw = await self._call_llm(
                system_prompt=SPACE_SYSTEM_PROMPT,
                user_message=user_message,
                json_mode=True,
                temperature=0.2,
            )
            return _parse_space_analysis(raw)
        except Exception as exc:
            logger.warning("Space Agent analysis failed: %s", exc)
            return SpaceAnalysis.fallback()


# ── Parser ────────────────────────────────────────────────────────────────────

def _parse_space_analysis(raw: str) -> SpaceAnalysis:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Space analysis JSON parse error: {exc}") from exc

    return SpaceAnalysis(
        assessment=data.get("assessment", ""),
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
