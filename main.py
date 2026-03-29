from contextlib import asynccontextmanager

from fastapi import FastAPI

from bot.webhook import router as webhook_router
from db.models import Base
from db.session import engine
from utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
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
