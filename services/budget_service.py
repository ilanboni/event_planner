from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from memory import reader, writer
from memory.schema import BudgetSummarySchema


_SKIP_STATUSES = {"rejected", "cancelled"}


async def recalculate(session: AsyncSession, event_id: str) -> BudgetSummarySchema:
    vendors = await reader.load_vendors(session, event_id)
    budget = await reader.load_budget_summary(session, event_id)
    if budget is None:
        raise ValueError(f"BudgetSummary for event {event_id} not found")

    total_committed = 0.0
    total_estimated = 0.0
    alerts = []
    now = datetime.utcnow().isoformat()

    for v in vendors:
        if v.status in _SKIP_STATUSES:
            continue

        # Best cost estimate for this vendor
        best_cost = v.confirmed_cost if v.confirmed_cost is not None else v.quoted_cost

        if best_cost is not None:
            total_estimated += best_cost

        if v.status == "confirmed":
            if v.confirmed_cost is not None:
                total_committed += v.confirmed_cost
            elif v.quoted_cost is not None:
                total_committed += v.quoted_cost
            else:
                # Confirmed vendor with no cost at all — flag it
                alerts.append({
                    "type": "unbudgeted_item",
                    "message": f"Confirmed vendor '{v.name}' has no cost recorded.",
                    "domain": "vendors",
                    "amount": None,
                    "created_at": now,
                    "acknowledged": False,
                })

    # Determine budget status
    ceiling = budget.total_ceiling
    if ceiling and ceiling > 0:
        ratio = total_estimated / ceiling
        if ratio > 1.10:
            status = "over"
        elif ratio > 1.00:
            status = "at_risk"
        elif ratio > 0.85:
            status = "watch"
        else:
            status = "healthy"

        if ratio > 1.00:
            over_by = total_estimated - ceiling
            alerts.append({
                "type": "overrun",
                "message": f"Estimated spend exceeds ceiling by €{over_by:,.0f}.",
                "domain": "budget",
                "amount": over_by,
                "created_at": now,
                "acknowledged": False,
            })
        elif ratio > 0.90:
            alerts.append({
                "type": "approaching_ceiling",
                "message": f"Estimated spend is {ratio * 100:.0f}% of the ceiling.",
                "domain": "budget",
                "amount": total_estimated,
                "created_at": now,
                "acknowledged": False,
            })
    else:
        status = "healthy"

    # Preserve previously acknowledged alerts so we don't re-surface them
    existing_acknowledged = [a for a in budget.alerts if a.acknowledged]
    existing_ack_dicts = [a.model_dump() for a in existing_acknowledged]
    final_alerts = existing_ack_dicts + alerts

    return await writer.update_budget_summary(
        session=session,
        event_id=event_id,
        total_committed=total_committed,
        total_estimated=total_estimated,
        budget_status=status,
        alerts=final_alerts,
    )


async def set_ceiling(session: AsyncSession, event_id: str, amount: float) -> BudgetSummarySchema:
    await writer.update_budget_summary(session=session, event_id=event_id, total_ceiling=amount)
    return await recalculate(session, event_id)


async def get_summary(session: AsyncSession, event_id: str) -> BudgetSummarySchema | None:
    return await reader.load_budget_summary(session, event_id)
