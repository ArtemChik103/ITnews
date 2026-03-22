from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.article import Article
from app.schemas.article import ArticleDetailRead, ArticleListResponse, ArticleRead
from app.schemas.search import (
    ClusterSummaryResponse,
    EntityDetailResponse,
    GraphNode,
    GraphResponse,
    SearchRequest,
    SearchResponse,
    SemanticSearchResponse,
)
from app.services.clustering.service import ClusteringService
from app.services.graph.neo4j import Neo4jGraphService
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


@router.get("/api/meta")
async def get_meta(session: AsyncSession = Depends(get_db_session)) -> dict:
    sources = (await session.scalars(select(distinct(Article.source)).where(Article.source.isnot(None)).order_by(Article.source))).all()
    languages = (await session.scalars(select(distinct(Article.language)).where(Article.language.isnot(None)).order_by(Article.language))).all()
    return {"sources": sources, "languages": languages}


@router.get("/api/articles", response_model=ArticleListResponse)
async def list_articles(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    source: str | None = None,
    language: str | None = None,
    cluster_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    entity: str | None = None,
    sort: str = Query(default="published_at", pattern="^(published_at|ingested_at)$"),
    session: AsyncSession = Depends(get_db_session),
) -> ArticleListResponse:
    query = select(Article)
    count_query = select(func.count(Article.id))

    if source:
        query = query.where(Article.source == source)
        count_query = count_query.where(Article.source == source)
    if language:
        query = query.where(Article.language == language)
        count_query = count_query.where(Article.language == language)
    if cluster_id is not None:
        query = query.where(Article.cluster_id == cluster_id)
        count_query = count_query.where(Article.cluster_id == cluster_id)
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
        except ValueError:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
        query = query.where(Article.published_at >= dt_from)
        count_query = count_query.where(Article.published_at >= dt_from)
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
        except ValueError:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d")
        # Include the entire day
        dt_to = dt_to.replace(hour=23, minute=59, second=59)
        query = query.where(Article.published_at <= dt_to)
        count_query = count_query.where(Article.published_at <= dt_to)

    total = await session.scalar(count_query) or 0

    sort_col = Article.published_at if sort == "published_at" else Article.ingested_at
    query = query.order_by(desc(sort_col)).offset((page - 1) * page_size).limit(page_size)
    result = await session.scalars(query)
    articles = result.all()

    if entity:
        graph_service = Neo4jGraphService()
        try:
            entity_detail = await graph_service.get_entity_detail(entity)
            if entity_detail:
                entity_article_ids = {a["article_id"] for a in entity_detail["articles"]}
                articles = [a for a in articles if a.id in entity_article_ids]
        finally:
            await graph_service.close()

    return ArticleListResponse(
        items=[ArticleRead.model_validate(a) for a in articles],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/api/articles/{article_id}", response_model=ArticleDetailRead)
async def get_article_detail(
    article_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> ArticleDetailRead:
    article = await session.get(Article, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")

    graph_service = Neo4jGraphService()
    try:
        entities_raw = await graph_service.get_article_entities(article_id)
        graph_data = await graph_service.get_graph_for_article(article_id, max_nodes=10)
        entity_details = []
        for name in entities_raw:
            entity_details.append({"name": name})
    finally:
        await graph_service.close()

    related_query = (
        select(Article)
        .where(Article.cluster_id == article.cluster_id, Article.id != article.id)
        .order_by(desc(Article.published_at))
        .limit(5)
    )
    related = []
    if article.cluster_id is not None:
        related_result = await session.scalars(related_query)
        related = [
            {"id": r.id, "title": r.title, "source": r.source, "url": r.url, "published_at": r.published_at.isoformat() if r.published_at else None}
            for r in related_result.all()
        ]

    return ArticleDetailRead(
        id=article.id,
        title=article.title,
        content_clean=article.content_clean or "",
        source=article.source,
        url=article.url,
        published_at=article.published_at,
        language=article.language,
        cluster_id=article.cluster_id,
        entities=entity_details,
        related_articles=related,
    )


@router.get("/api/graph", response_model=GraphResponse)
async def get_graph(
    article_id: int | None = None,
    entity_name: str | None = None,
    query: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> GraphResponse:
    graph_service = Neo4jGraphService()
    try:
        if article_id is not None:
            data = await graph_service.get_graph_for_article(article_id)
        elif entity_name is not None:
            data = await graph_service.get_graph_for_entity(entity_name)
        elif query is not None:
            articles = await RetrievalService(session).semantic_search(query, top_k=5)
            if articles:
                article_ids = [a.article_id for a in articles]
                ctx = await graph_service.get_context(article_ids, max_entities=50, max_relations=80)
                data = {
                    "nodes": [{"name": e["name"], "type": e["type"], "id": e["name"].lower().replace(" ", "_")} for e in ctx["entities"]],
                    "edges": ctx["edges"],
                }
            else:
                data = {"nodes": [], "edges": []}
        else:
            data = {"nodes": [], "edges": []}
    finally:
        await graph_service.close()

    nodes = [
        GraphNode(
            id=n.get("id", n["name"]).lower().replace(" ", "_"),
            label=n["name"],
            type=n.get("type", "Entity"),
            metadata={},
        )
        for n in data.get("nodes", [])
    ]
    edges_raw = data.get("edges", [])
    from app.schemas.search import GraphEdge

    edges = []
    for e in edges_raw:
        from_name = e.get("from_name") or e.get("from", "")
        to_name = e.get("to_name") or e.get("to", "")
        edges.append(GraphEdge(**{
            "from": from_name,
            "relation": e.get("relation", "RELATED_TO"),
            "to": to_name,
            "source_article_ids": e.get("source_article_ids", []),
        }))

    return GraphResponse(nodes=nodes[:50], edges=edges[:80])


@router.get("/api/entities/{entity_name}", response_model=EntityDetailResponse)
async def get_entity_detail_route(entity_name: str) -> EntityDetailResponse:
    graph_service = Neo4jGraphService()
    try:
        detail = await graph_service.get_entity_detail(entity_name)
    finally:
        await graph_service.close()

    if detail is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    from app.schemas.search import EntityArticle, SearchEntity

    return EntityDetailResponse(
        name=detail["name"],
        type=detail["type"],
        articles=[
            EntityArticle(
                article_id=a["article_id"],
                title=a.get("title", ""),
                source=a.get("source", ""),
                url=a.get("url", ""),
                published_at=a.get("published_at"),
            )
            for a in detail["articles"]
        ],
        related_entities=[
            SearchEntity(name=r["name"], type=r["type"])
            for r in detail["related_entities"]
        ],
    )


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
