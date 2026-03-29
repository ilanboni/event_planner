from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.lead_agent import LeadAgent, MemoryWrite, SynthesisResult
from bot.message_handler import IncomingMessage
from db.models import Message
from db.session import AsyncSessionLocal
from memory import writer as mem_writer
from memory.summary import serialize_files
from orchestrator.context_loader import load_baseline, load_for_domains, to_prompt_string
from orchestrator.router import RouterResult, route
from services import decision_service, issue_service
from utils.logger import logger

# Module-level singleton — one instance shared across all requests
_lead_agent = LeadAgent()


# ── Public entry point ────────────────────────────────────────────────────────

async def process(message: IncomingMessage, event_id: str) -> str:
    """
    Full A–J orchestration pipeline. Returns the text to send to the user.

    Steps:
      A  Handle attachment (Archivist) if present
      B  Deterministic routing
      C  Load baseline memory
      D  Lead Agent classification (if deterministic routing deferred)
      E  Load full domain context
      F  Load recent conversation history
      G  Lead Agent synthesis
      H  Execute memory writes
      I  Update context summary
      J  Return response text
    """
    async with AsyncSessionLocal() as session:
        try:
            return await _run(session, message, event_id)
        except Exception as exc:
            logger.exception("Pipeline error for event_id=%s: %s", event_id, exc)
            return "I ran into an issue on my end. Please try again in a moment."


# ── Pipeline steps ────────────────────────────────────────────────────────────

async def _run(
    session: AsyncSession,
    message: IncomingMessage,
    event_id: str,
) -> str:

    # ── A: Attachment handling ────────────────────────────────────────────────
    archivist_output: dict | None = None
    if message.attachments:
        archivist_output = await _handle_attachments(session, event_id, message)

    # ── B: Deterministic routing ──────────────────────────────────────────────
    router_result: RouterResult = route(message)
    logger.info(
        "Router: method=%s domains=%s",
        router_result.routing_method,
        router_result.domains_involved,
    )

    # ── C: Load baseline memory ───────────────────────────────────────────────
    baseline_context = await load_baseline(session, event_id)

    # ── D: Lead Agent classification (when deterministic routing deferred) ────
    if router_result.routing_method == "lead_agent":
        baseline_str = to_prompt_string(baseline_context)
        routing = await _lead_agent.classify(
            message_text=message.text or "",
            baseline_context=baseline_str,
        )
        if routing.clarification_needed and routing.clarification_question:
            logger.info("Lead Agent requesting clarification")
            return routing.clarification_question
        domains = routing.domains_involved
    else:
        domains = router_result.domains_involved

    # ── E: Load full domain context ───────────────────────────────────────────
    full_context = await load_for_domains(session, event_id, domains)

    # Inject archivist output into context summary if files are pending
    # (context_loader already loads files_pending; this supplements it
    #  with the freshly processed output from this session's upload)
    if archivist_output:
        _inject_archivist_into_context(full_context, archivist_output)

    # ── F: Recent conversation history ────────────────────────────────────────
    recent_messages = await _load_recent_messages(session, event_id)

    # ── G: Lead Agent synthesis ───────────────────────────────────────────────
    full_context_str = to_prompt_string(full_context)
    synthesis: SynthesisResult = await _lead_agent.synthesize(
        message_text=message.text or "",
        full_context=full_context_str,
        archivist_output=archivist_output,
        recent_messages=recent_messages,
    )

    # ── H: Execute memory writes ──────────────────────────────────────────────
    if synthesis.memory_writes:
        await _execute_memory_writes(session, event_id, synthesis.memory_writes)

    # ── I: Update context summary ─────────────────────────────────────────────
    if synthesis.context_summary_update:
        try:
            await mem_writer.update_working_notes_summary(
                session, event_id, synthesis.context_summary_update
            )
        except Exception as exc:
            logger.warning("Failed to update context summary: %s", exc)

    # ── J: Return response ────────────────────────────────────────────────────
    return synthesis.response_text


# ── Memory write dispatcher ───────────────────────────────────────────────────

async def _execute_memory_writes(
    session: AsyncSession,
    event_id: str,
    writes: list[MemoryWrite],
) -> None:
    for write in writes:
        try:
            await _dispatch_write(session, event_id, write)
        except Exception as exc:
            logger.error(
                "Memory write failed section=%s op=%s: %s",
                write.section, write.operation, exc,
            )


async def _dispatch_write(
    session: AsyncSession,
    event_id: str,
    write: MemoryWrite,
) -> None:
    s, op, data = write.section, write.operation, write.data

    if s == "confirmed_decisions" and op == "create":
        await decision_service.create_decision(
            session=session,
            event_id=event_id,
            domain=data.get("domain", "general"),
            title=data.get("title", "Untitled decision"),
            description=data.get("description", ""),
            source=data.get("source", "lead_agent"),
            decided_by=data.get("decided_by", "lead_agent"),
            supersedes_id=data.get("supersedes_id"),
            notes=data.get("notes"),
        )
        logger.info("Decision written: %s", data.get("title"))

    elif s == "open_issues" and op == "create":
        await issue_service.create_issue(
            session=session,
            event_id=event_id,
            domain=data.get("domain", "general"),
            title=data.get("title", "Untitled issue"),
            description=data.get("description", ""),
            priority=data.get("priority", "medium"),
            created_by=data.get("created_by", "lead_agent"),
        )
        logger.info("Issue created: %s", data.get("title"))

    elif s == "client_profile" and op == "append_note":
        await mem_writer.append_raw_note(
            session=session,
            event_id=event_id,
            text=data.get("text", ""),
            source=data.get("source", "lead_observation"),
        )

    elif s == "working_notes" and op == "update_summary":
        await mem_writer.update_working_notes_summary(
            session=session,
            event_id=event_id,
            summary=data.get("summary", ""),
        )

    else:
        logger.warning("Unhandled memory write: section=%s op=%s", s, op)


# ── Attachment handling ───────────────────────────────────────────────────────

async def _handle_attachments(
    session: AsyncSession,
    event_id: str,
    message: IncomingMessage,
) -> dict | None:
    """
    Download and process the first attachment via the Archivist.
    Returns the archivist structured output, or None if processing fails.
    Multi-attachment messages are supported by Telegram but rare; we process
    the first and log the rest.
    """
    if len(message.attachments) > 1:
        logger.info("Message has %d attachments; processing first only", len(message.attachments))

    attachment = message.attachments[0]

    try:
        # Phase 3 modules — imported here to avoid hard failures if Phase 3
        # was not fully implemented yet.
        from bot.attachment_handler import download_attachment
        from agents.archivist import ArchivistAgent
        from files.classifier import classify_file
        from files.extractor import extract_text
        from services.file_service import create_record, mark_processed

        # Download
        local_path = await download_attachment(attachment)

        # Preliminary classification (filename + MIME)
        file_type = classify_file(
            filename=attachment.file_name or f"file.{attachment.mime_type.split('/')[-1]}",
            mime_type=attachment.mime_type,
        )

        # Create DB record
        file_record = await create_record(
            session=session,
            event_id=event_id,
            original_filename=attachment.file_name or "upload",
            storage_path=local_path,
            file_type=file_type.value,
        )

        # Extract text (where possible)
        extracted_text = await extract_text(local_path, attachment.mime_type)

        # Re-classify with text if available
        if extracted_text:
            file_type = classify_file(
                filename=attachment.file_name or "",
                mime_type=attachment.mime_type,
                extracted_text=extracted_text,
            )

        # Archivist analysis
        archivist = ArchivistAgent()
        output = await archivist.process(
            file_id=file_record.id,
            file_path=local_path,
            file_type=file_type,
            extracted_text=extracted_text,
        )

        # Persist extraction
        await mark_processed(
            session=session,
            file_id=file_record.id,
            summary=output.get("summary", ""),
            extracted_data=output.get("extracted_data", {}),
            linked_domains=output.get("linked_domains", []),
        )

        logger.info("Archivist processed file_id=%s type=%s", file_record.id, file_type.value)
        return output

    except ImportError as exc:
        logger.warning("Phase 3 module not available (%s) — skipping attachment", exc)
        return None
    except Exception as exc:
        logger.error("Attachment handling failed: %s", exc)
        return None


def _inject_archivist_into_context(context, archivist_output: dict) -> None:
    """
    If the context has no files_pending section yet, inject a brief
    summary of the freshly processed file so the Lead Agent sees it.
    """
    if context.files_pending is None and archivist_output:
        summary = archivist_output.get("summary", "")
        file_type = archivist_output.get("file_type", "file")
        context.files_pending = (
            f"=== FILES ===\n"
            f"  [{file_type}] (just uploaded) | PENDING LEAD REVIEW\n"
            f"    {summary}"
        )


# ── Recent message loader ─────────────────────────────────────────────────────

async def _load_recent_messages(
    session: AsyncSession,
    event_id: str,
    limit: int = 6,
) -> list[str]:
    """
    Load the last `limit` messages for this event in chronological order.
    Returns a list of "Client: …" / "You: …" strings for the synthesis prompt.
    """
    result = await session.execute(
        select(Message)
        .where(Message.event_id == event_id)
        .where(Message.text.isnot(None))
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    rows = list(reversed(result.scalars().all()))
    formatted: list[str] = []
    for row in rows:
        label = "Client" if row.direction == "incoming" else "You"
        formatted.append(f"{label}: {row.text}")
    return formatted
