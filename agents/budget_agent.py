from __future__ import annotations

import json
from dataclasses import dataclass, field

from agents.base import BaseAgent
from prompts.budget_agent import BUDGET_SYSTEM_PROMPT
from utils.logger import logger


# ── Output dataclass ──────────────────────────────────────────────────────────

@dataclass
class BudgetAnalysis:
    """
    Structured briefing produced by the Budget Agent.
    Passed to the Lead Agent as specialist_output; never sent to the client.
    """
    summary: str
    budget_status: str                        # healthy | watch | at_risk | over | unknown
    budget_ceiling: float | None
    total_committed: float | None
    total_estimated: float | None
    headroom: float | None                    # ceiling - total_estimated, or None
    relevant_vendors: list[dict] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    proposed_decisions: list[dict] = field(default_factory=list)
    proposed_issues: list[dict] = field(default_factory=list)
    clarification_needed: bool = False
    clarification_question: str | None = None

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "budget_status": self.budget_status,
            "budget_ceiling": self.budget_ceiling,
            "total_committed": self.total_committed,
            "total_estimated": self.total_estimated,
            "headroom": self.headroom,
            "relevant_vendors": self.relevant_vendors,
            "flags": self.flags,
            "proposed_decisions": self.proposed_decisions,
            "proposed_issues": self.proposed_issues,
            "clarification_needed": self.clarification_needed,
            "clarification_question": self.clarification_question,
        }

    @classmethod
    def fallback(cls) -> BudgetAnalysis:
        return cls(
            summary="Budget analysis unavailable — check logs.",
            budget_status="unknown",
            budget_ceiling=None,
            total_committed=None,
            total_estimated=None,
            headroom=None,
        )


# ── Agent ─────────────────────────────────────────────────────────────────────

class BudgetAgent(BaseAgent):
    """
    Internal financial analyst specialist.

    Receives the serialized vendor + budget context and the client message.
    Returns a BudgetAnalysis that the Lead Agent uses when composing
    the final response and deciding which memory writes to execute.

    Never raises — falls back to BudgetAnalysis.fallback().
    """

    async def analyze(
        self,
        message_text: str,
        budget_context: str,
    ) -> BudgetAnalysis:
        user_message = (
            f"BUDGET AND VENDOR CONTEXT:\n{budget_context}\n\n"
            f"CLIENT MESSAGE:\n{message_text or '(no text)'}\n\n"
            "Return your analysis as a JSON object."
        )

        try:
            raw = await self._call_llm(
                system_prompt=BUDGET_SYSTEM_PROMPT,
                user_message=user_message,
                json_mode=True,
                temperature=0.1,
            )
            return _parse_budget_analysis(raw)
        except Exception as exc:
            logger.warning("Budget Agent analysis failed: %s", exc)
            return BudgetAnalysis.fallback()


# ── Parser ────────────────────────────────────────────────────────────────────

def _parse_budget_analysis(raw: str) -> BudgetAnalysis:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Budget analysis JSON parse error: {exc}") from exc

    return BudgetAnalysis(
        summary=data.get("summary", ""),
        budget_status=data.get("budget_status", "unknown"),
        budget_ceiling=_to_float(data.get("budget_ceiling")),
        total_committed=_to_float(data.get("total_committed")),
        total_estimated=_to_float(data.get("total_estimated")),
        headroom=_to_float(data.get("headroom")),
        relevant_vendors=_coerce_list_of_dicts(data.get("relevant_vendors")),
        flags=_coerce_str_list(data.get("flags")),
        proposed_decisions=_coerce_list_of_dicts(data.get("proposed_decisions")),
        proposed_issues=_coerce_list_of_dicts(data.get("proposed_issues")),
        clarification_needed=bool(data.get("clarification_needed", False)),
        clarification_question=data.get("clarification_question") or None,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_list_of_dicts(value) -> list[dict]:
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    return []


def _coerce_str_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    return []
