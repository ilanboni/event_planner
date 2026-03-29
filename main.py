from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from bot.webhook import router as webhook_router
from config import settings
from db.models import Base
from db.session import engine
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
    yield
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(title="Event Planner Bot", lifespan=lifespan)

app.include_router(webhook_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "event-planner-bot"}
