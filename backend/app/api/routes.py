from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.article import ArticleRead
from app.services.graph.pipeline import graph_article
from app.services.health import run_healthcheck
from app.services.ingestion.pipeline import IngestionPipeline

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return await run_healthcheck()


@router.post("/ingestion/run")
async def run_ingestion(session: AsyncSession = Depends(get_db_session)) -> dict:
    return await IngestionPipeline(session).run()


@router.get("/articles", response_model=list[ArticleRead])
async def list_articles(session: AsyncSession = Depends(get_db_session)) -> list[ArticleRead]:
    return list(await IngestionPipeline(session).list_articles())


@router.post("/articles/{article_id}/graph")
async def process_article_graph(article_id: int, session: AsyncSession = Depends(get_db_session)) -> dict:
    article = await IngestionPipeline(session).get_article(article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return await graph_article(article)
