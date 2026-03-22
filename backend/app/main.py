from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import Article  # noqa: F401
from app.services.ingestion.pipeline import IngestionPipeline

settings = get_settings()
scheduler = AsyncIOScheduler(timezone="UTC")


async def run_scheduled_ingestion() -> None:
    async with SessionLocal() as session:
        await IngestionPipeline(session).run()


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    if settings.enable_scheduler and not scheduler.running:
        scheduler.add_job(run_scheduled_ingestion, "interval", minutes=settings.ingestion_interval_minutes)
        scheduler.start()

    yield

    if scheduler.running:
        scheduler.shutdown(wait=False)
    await engine.dispose()


app = FastAPI(title=settings.project_name, lifespan=lifespan)
app.include_router(router)
