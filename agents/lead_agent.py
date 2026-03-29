from __future__ import annotations

import json
from dataclasses import dataclass, field

from agents.base import BaseAgent
from prompts.lead_agent import CLASSIFICATION_PROMPT, SYNTHESIS_PROMPT
from utils.logger import logger


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class RoutingDecision:
    message_type: str
    domains_involved: list[str]
    memory_sections_needed: list[str]
    specialists_to_call: list[str]
    requires_lead_synthesis: bool
    clarification_needed: bool
    clarification_question: str | None

    @classmethod
    def direct_answer(cls) -> RoutingDecision:
        """Fallback used when classification itself fails."""
        return cls(
            message_type="ambiguous",
            domains_involved=[],
            memory_sections_needed=[],
            specialists_to_call=[],
            requires_lead_synthesis=True,
            clarification_needed=False,
            clarification_question=None,
        )


@dataclass
class MemoryWrite:
    section: str
    operation: str
    data: dict


@dataclass
class SynthesisResult:
    response_text: str
    memory_writes: list[MemoryWrite] = field(default_factory=list)
    context_summary_update: str | None = None

    @classmethod
    def fallback(cls, message: str = "I'm having trouble right now. Please try again in a moment.") -> SynthesisResult:
        return cls(response_text=message)


# ── Lead Agent ────────────────────────────────────────────────────────────────

class LeadAgent(BaseAgent):
    """
    The Lead Agent operates in two modes:

      classify()   — fast routing call; reads baseline memory, returns a
                     RoutingDecision that tells the pipeline what to load.

      synthesize() — full persona call; reads complete loaded context, produces
                     a user-facing response and structured memory writes.
    """

    async def classify(
        self,
        message_text: str,
        baseline_context: str,
    ) -> RoutingDecision:
        """
        Classify the incoming message and determine routing.
        Returns a RoutingDecision. Never raises — falls back to direct_answer().
        """
        user_message = (
            f"CURRENT EVENT MEMORY:\n{baseline_context}\n\n"
            f"CLIENT MESSAGE:\n{message_text or '(no text — attachment only)'}\n\n"
            "Return your routing decision as a JSON object."
        )

        try:
            raw = await self._call_llm(
                system_prompt=CLASSIFICATION_PROMPT,
                user_message=user_message,
                json_mode=True,
                temperature=0.1,
            )
            return _parse_routing_decision(raw)
        except Exception as exc:
            logger.warning("Lead Agent classification failed: %s", exc)
            return RoutingDecision.direct_answer()

    async def synthesize(
        self,
        message_text: str,
        full_context: str,
        archivist_output: dict | None = None,
        recent_messages: list[str] | None = None,
        specialist_outputs: dict[str, dict] | None = None,
    ) -> SynthesisResult:
        """
        Generate the final user response and memory write instructions.
        Never raises — falls back to SynthesisResult.fallback().
        """
        from prompts.builders import build_lead_synthesis_message
        from orchestrator.context_loader import LoadedContext

        # Build a minimal LoadedContext shell so the builder can assemble
        # the message. The context string itself is already serialized.
        # We pass it directly instead of re-serializing.
        user_message = _build_synthesis_user_message(
            full_context=full_context,
            message_text=message_text,
            archivist_output=archivist_output,
            recent_messages=recent_messages,
            specialist_outputs=specialist_outputs,
        )

        try:
            raw = await self._call_llm(
                system_prompt=SYNTHESIS_PROMPT,
                user_message=user_message,
                json_mode=True,
                temperature=0.5,
            )
            return _parse_synthesis_result(raw)
        except Exception as exc:
            logger.error("Lead Agent synthesis failed: %s", exc)
            return SynthesisResult.fallback()


# ── Parsers ───────────────────────────────────────────────────────────────────

def _parse_routing_decision(raw: str) -> RoutingDecision:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Classification JSON parse error: {exc}") from exc

    return RoutingDecision(
        message_type=data.get("message_type", "ambiguous"),
        domains_involved=_coerce_list(data.get("domains_involved")),
        memory_sections_needed=_coerce_list(data.get("memory_sections_needed")),
        specialists_to_call=[],   # Phase 4: never call specialists
        requires_lead_synthesis=True,
        clarification_needed=bool(data.get("clarification_needed", False)),
        clarification_question=data.get("clarification_question") or None,
    )


def _parse_synthesis_result(raw: str) -> SynthesisResult:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Synthesis JSON parse error: %s — raw: %s…", exc, raw[:200])
        # If the model returned something that is not valid JSON, surface the
        # raw text as the response rather than a generic error message.
        return SynthesisResult(response_text=_extract_text_fallback(raw))

    response_text = data.get("response_text", "").strip()
    if not response_text:
        logger.warning("Synthesis returned empty response_text")
        response_text = "Understood. I've noted that."

    raw_writes = data.get("memory_writes") or []
    memory_writes = [
        MemoryWrite(
            section=w.get("section", ""),
            operation=w.get("operation", ""),
            data=w.get("data", {}),
        )
        for w in raw_writes
        if isinstance(w, dict) and w.get("section") and w.get("operation")
    ]

    return SynthesisResult(
        response_text=response_text,
        memory_writes=memory_writes,
        context_summary_update=data.get("context_summary_update") or None,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

# Human-readable section headers for each specialist.
# Add an entry here whenever a new specialist is integrated.
_SPECIALIST_LABELS: dict[str, str] = {
    "budget":   "BUDGET SPECIALIST ANALYSIS",
    "space":    "SPACE SPECIALIST ANALYSIS",
    "timeline": "TIMELINE SPECIALIST ANALYSIS",
}


def _build_synthesis_user_message(
    full_context: str,
    message_text: str,
    archivist_output: dict | None,
    recent_messages: list[str] | None,
    specialist_outputs: dict[str, dict] | None = None,
) -> str:
    parts: list[str] = [f"FULL EVENT MEMORY:\n{full_context}"]

    if recent_messages:
        parts.append("RECENT CONVERSATION (oldest first):\n" + "\n".join(recent_messages))

    if specialist_outputs:
        for name, data in specialist_outputs.items():
            label = _SPECIALIST_LABELS.get(name, f"{name.upper()} SPECIALIST ANALYSIS")
            parts.append(f"{label}:\n{json.dumps(data, indent=2, ensure_ascii=False)}")

    if archivist_output:
        parts.append(
            "ARCHIVIST FILE ANALYSIS:\n"
            + json.dumps(archivist_output, indent=2, ensure_ascii=False)
        )

    parts.append(f"CLIENT MESSAGE:\n{message_text or '(no text — see file analysis above)'}")
    parts.append("Return your response as a JSON object.")

    return "\n\n".join(parts)


def _coerce_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


def _extract_text_fallback(raw: str) -> str:
    """
    If the model returned prose instead of JSON (rare but possible),
    attempt to use it directly. Strip any obvious JSON artifacts.
    """
    stripped = raw.strip().strip("`").strip()
    if len(stripped) > 20:
        return stripped
    return "I've received your message. Let me follow up shortly."
