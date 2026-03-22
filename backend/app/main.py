from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.db.base import Base
from app.db.schema import ensure_article_schema
from app.db.session import SessionLocal, engine
from app.models import Article  # noqa: F401
from app.services.clustering.service import ClusteringService
from app.services.graph.neo4j import Neo4jGraphService
from app.services.indexing import pipeline as indexing_pipeline
from app.services.indexing.pipeline import IndexingPipeline
from app.services.ingestion.pipeline import IngestionPipeline
from app.services.vector_store.service import VectorStoreService

settings = get_settings()
scheduler = AsyncIOScheduler(timezone="UTC")


async def run_scheduled_ingestion() -> None:
    async with SessionLocal() as session:
        await IngestionPipeline(session).run()


async def run_scheduled_indexing() -> None:
    async with SessionLocal() as session:
        result = await IndexingPipeline(session).run()
        if result["trigger_recluster"]:
            await ClusteringService(session).recluster()
            indexing_pipeline.indexed_since_recluster = 0


async def run_scheduled_clustering() -> None:
    async with SessionLocal() as session:
        await ClusteringService(session).recluster()
        indexing_pipeline.indexed_since_recluster = 0


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await ensure_article_schema(engine)
    vector_store = VectorStoreService()
    await vector_store.ensure_collection()
    await vector_store.close()
    graph = Neo4jGraphService()
    await graph.initialize()
    await graph.close()

    if settings.enable_scheduler and not scheduler.running:
        scheduler.add_job(run_scheduled_ingestion, "interval", minutes=settings.ingestion_interval_minutes)
        scheduler.add_job(run_scheduled_indexing, "interval", minutes=settings.embedding_index_interval_minutes)
        scheduler.add_job(run_scheduled_clustering, "interval", minutes=settings.clustering_interval_minutes)
        scheduler.start()

    yield

    if scheduler.running:
        scheduler.shutdown(wait=False)
    await engine.dispose()


app = FastAPI(title=settings.project_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
