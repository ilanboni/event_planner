import asyncio

from db.models import (
    Base, BudgetSummary, ClientProfile, DesignBrief,
    Event, GuestSummary, TimelineDraft, WorkingNotes,
)
from db.session import AsyncSessionLocal, engine

# ── Update these values before first run ──────────────────────────────────────
SEED_EVENT = {
    "event_name": "Bat Mitzvah",
    "event_date": "2025-10-18",           # YYYY-MM-DD
    "event_time_start": "16:00",
    "event_time_end_estimated": "23:00",
    "venue_name": "Villa Miani",           # already booked
    "venue_address": "Via Trionfale 151, Roma",
    "venue_booked": True,
    "guest_count_estimated": 80,
    "client_name": "Client Name",          # update before use
    "client_telegram_id": "REPLACE_ME",   # Telegram user ID as string
    "honoree_name": "Honoree Name",        # update before use
    "ceremony_type": "Reception",
}
# ─────────────────────────────────────────────────────────────────────────────


async def create_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")


async def seed_event() -> None:
    async with AsyncSessionLocal() as session:
        event = Event(**SEED_EVENT)
        session.add(event)
        await session.flush()  # Populate event.id before dependent inserts

        session.add(ClientProfile(event_id=event.id))
        session.add(BudgetSummary(event_id=event.id))
        session.add(GuestSummary(event_id=event.id))
        session.add(DesignBrief(event_id=event.id))
        session.add(TimelineDraft(event_id=event.id))
        session.add(WorkingNotes(event_id=event.id))

        await session.commit()

        print(f"Event seeded:         id={event.id}")
        print(f"client_telegram_id:   {event.client_telegram_id}")
        print(f"Venue:                {event.venue_name}")
        print(f"Date:                 {event.event_date}")


async def main() -> None:
    await create_tables()
    await seed_event()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
