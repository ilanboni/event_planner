from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from memory import reader, writer
from memory.schema import FileRecordSchema


async def create_record(
    session: AsyncSession,
    event_id: str,
    original_filename: str,
    storage_path: str,
    file_type: str = "other",
) -> FileRecordSchema:
    return await writer.create_file_record(
        session=session,
        event_id=event_id,
        original_filename=original_filename,
        storage_path=storage_path,
        file_type=file_type,
    )


async def mark_processed(
    session: AsyncSession,
    file_id: str,
    summary: str,
    extracted_data: dict,
    linked_domains: list[str],
) -> FileRecordSchema:
    return await writer.mark_file_processed(
        session=session,
        file_id=file_id,
        summary=summary,
        extracted_data=extracted_data,
        linked_domains=linked_domains,
    )


async def mark_lead_reviewed(
    session: AsyncSession,
    file_id: str,
    action_taken: str,
) -> FileRecordSchema:
    return await writer.mark_file_lead_reviewed(
        session=session,
        file_id=file_id,
        action_taken=action_taken,
    )


async def get_unreviewed(
    session: AsyncSession,
    event_id: str,
) -> list[FileRecordSchema]:
    return await reader.load_files(session=session, event_id=event_id, unreviewed_only=True)
