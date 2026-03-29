from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import select

from bot.webhook import router as webhook_router
from config import settings
from db.models import Base, Event
from db.session import AsyncSessionLocal, engine
from utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure file storage directory exists before the first upload
    Path(settings.FILES_STORAGE_PATH).mkdir(parents=True, exist_ok=True)

    # Ensure the database file's parent directory exists (important for
    # SQLite on Railway where DATABASE_URL points to a mounted volume path)
    if "sqlite" in settings.DATABASE_URL:
        db_file = settings.DATABASE_URL.split("///")[-1]
        if db_file:
            Path(db_file).parent.mkdir(parents=True, exist_ok=True)

    logger.info("Startup: initialising database")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database ready")

    # Auto-seed on first startup if no events exist
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Event).limit(1))
        if result.scalar_one_or_none() is None:
            logger.info("No events found — running seed")
            from seed import seed_event
            await seed_event()
            logger.info("Seed complete")

    yield
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(title="Event Planner Bot", lifespan=lifespan)

app.include_router(webhook_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "event-planner-bot"}
