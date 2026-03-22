from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.article import ArticleRead
from app.schemas.search import ClusterSummaryResponse, SearchRequest, SearchResponse, SemanticSearchResponse
from app.services.clustering.service import ClusteringService
from app.services.graph.pipeline import graph_article
from app.services.health import run_healthcheck
from app.services.indexing.pipeline import IndexingPipeline
from app.services.ingestion.pipeline import IngestionPipeline
from app.services.rag.service import RagService
from app.services.retrieval.service import RetrievalService

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


@router.post("/indexing/run")
async def run_indexing(session: AsyncSession = Depends(get_db_session)) -> dict:
    return await IndexingPipeline(session).run()


@router.post("/clustering/run")
async def run_clustering(session: AsyncSession = Depends(get_db_session)) -> dict:
    return await ClusteringService(session).recluster()


@router.get("/api/search/semantic", response_model=SemanticSearchResponse)
async def semantic_search(
    q: str = Query(..., min_length=1),
    top_k: int = Query(default=5, ge=1, le=20),
    source: str | None = None,
    language: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> SemanticSearchResponse:
    items = await RetrievalService(session).semantic_search(
        query=q,
        top_k=top_k,
        filters={
            "source": source,
            "language": language,
            "date_from": date_from,
            "date_to": date_to,
        },
    )
    return SemanticSearchResponse(
        items=[
            {
                "article_id": item.article_id,
                "title": item.title,
                "source": item.source,
                "url": item.url,
                "published_at": item.published_at,
                "cluster_id": item.cluster_id,
                "score": item.score,
            }
            for item in items
        ],
        query=q,
        top_k=top_k,
    )


@router.get("/api/clusters", response_model=ClusterSummaryResponse)
async def list_clusters(session: AsyncSession = Depends(get_db_session)) -> ClusterSummaryResponse:
    return ClusterSummaryResponse(clusters=await ClusteringService(session).list_clusters())


@router.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest, session: AsyncSession = Depends(get_db_session)) -> SearchResponse:
    return await RagService(session).answer(
        question=request.question,
        top_k=request.top_k,
        use_graph=request.use_graph,
        filters={
            "date_from": request.date_from.isoformat() if request.date_from else None,
            "date_to": request.date_to.isoformat() if request.date_to else None,
            "source": request.source_filter[0] if request.source_filter and len(request.source_filter) == 1 else None,
            "sources": request.source_filter if request.source_filter and len(request.source_filter) > 1 else None,
        },
    )
