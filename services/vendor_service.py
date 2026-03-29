from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from memory import reader, writer
from memory.schema import VendorSchema


async def create_vendor(
    session: AsyncSession,
    event_id: str,
    name: str,
    category: str,
    notes: str | None = None,
) -> VendorSchema:
    return await writer.add_vendor(
        session=session,
        event_id=event_id,
        name=name,
        category=category,
        notes=notes,
    )


async def update_status(
    session: AsyncSession,
    vendor_id: str,
    new_status: str,
) -> VendorSchema:
    return await writer.update_vendor_fields(session=session, vendor_id=vendor_id, status=new_status)


async def set_cost(
    session: AsyncSession,
    vendor_id: str,
    quoted: float | None = None,
    confirmed: float | None = None,
) -> VendorSchema:
    fields: dict = {}
    if quoted is not None:
        fields["quoted_cost"] = quoted
    if confirmed is not None:
        fields["confirmed_cost"] = confirmed

    vendor = await writer.update_vendor_fields(session=session, vendor_id=vendor_id, **fields)

    # Recalculate budget after any cost change
    from services import budget_service
    await budget_service.recalculate(session, vendor.event_id)

    return vendor


async def get_vendors(
    session: AsyncSession,
    event_id: str,
    category: str | None = None,
    status: str | None = None,
) -> list[VendorSchema]:
    return await reader.load_vendors(
        session=session,
        event_id=event_id,
        category=category,
        status=status,
    )
