import asyncio

from utils.logger import logger
from db.models import (
    Base, BudgetSummary, ClientProfile, DesignBrief,
    Event, GuestSummary, TimelineDraft, WorkingNotes,
)
from db.session import AsyncSessionLocal, engine

# ── Update these values before first run ──────────────────────────────────────
SEED_EVENT = {
    "event_name": "Bat Mitzvah Sarah e Allegra",
    "event_date": "2026-06-07",           # YYYY-MM-DD
    "event_time_start": "16:00",
    "event_time_end_estimated": "23:00",
    "venue_name": "Pineta",
    "venue_address": "Milano",
    "venue_booked": True,
    "guest_count_estimated": 80,
    "client_name": "Marcia",
    "client_telegram_id": "7088757056",
    "honoree_name": "Sarah e Allegra",
    "ceremony_type": "Bat Mitzvah",
}
# ─────────────────────────────────────────────────────────────────────────────


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")


async def seed_event(session=None) -> None:
    """
    Insert the seed event and all companion records.
    Accepts an optional external session (used by main.py auto-seed).
    If no session is provided, opens its own.
    """
    async def _insert(s) -> None:
        event = Event(**SEED_EVENT)
        s.add(event)
        await s.flush()  # Populate event.id before dependent inserts

        s.add(ClientProfile(event_id=event.id))
        s.add(BudgetSummary(event_id=event.id))
        s.add(GuestSummary(event_id=event.id))
        s.add(DesignBrief(event_id=event.id))
        s.add(TimelineDraft(event_id=event.id))
        s.add(WorkingNotes(event_id=event.id))

        await s.commit()

        logger.info("Event seeded: id=%s telegram_id=%s", event.id, event.client_telegram_id)
        print(f"Event seeded:         id={event.id}")
        print(f"client_telegram_id:   {event.client_telegram_id}")
        print(f"Venue:                {event.venue_name}")
        print(f"Date:                 {event.event_date}")

    if session is not None:
        await _insert(session)
    else:
        async with AsyncSessionLocal() as s:
            await _insert(s)


async def main() -> None:
    await create_tables()
    await seed_event()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
