from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.article import Article
from app.services.embeddings.service import EmbeddingService
from app.services.graph.neo4j import Neo4jGraphService
from app.services.vector_store.service import VectorStoreService


@dataclass(slots=True)
class RetrievedArticle:
    article_id: int
    title: str
    source: str
    url: str
    published_at: datetime | None
    cluster_id: int | None
    score: float
    snippet: str
    entity_names: list[str]


@dataclass(slots=True)
class RetrievedGraphEdge:
    from_name: str
    relation: str
    to_name: str
    source_article_ids: list[int]


@dataclass(slots=True)
class RetrievalResult:
    articles: list[RetrievedArticle]
    entities: list[dict]
    graph_edges: list[RetrievedGraphEdge]
    graph_available: bool


class RetrievalService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.embedding_service = EmbeddingService()

    async def semantic_search(self, query: str, top_k: int, filters: dict | None = None) -> list[RetrievedArticle]:
        query_embedding = await self.embedding_service.generate(article_id=0, title=query, content_clean="", language="")
        if query_embedding.status != "ready" or not query_embedding.embedding:
            return []

        vector_store = VectorStoreService()
        try:
            hits = await vector_store.search(query_embedding.embedding, top_k=top_k * 3, filters=filters)
        finally:
            await vector_store.close()

        article_ids = [int(hit.id) for hit in hits]
        if not article_ids:
            return []

        articles = await self.session.scalars(select(Article).where(Article.id.in_(article_ids)))
        article_map = {article.id: article for article in articles}

        ranked: list[RetrievedArticle] = []
        for hit in hits:
            article = article_map.get(int(hit.id))
            if article is None:
                continue
            payload = hit.payload or {}
            ranked.append(
                RetrievedArticle(
                    article_id=article.id,
                    title=article.title,
                    source=article.source,
                    url=article.url,
                    published_at=article.published_at,
                    cluster_id=article.cluster_id,
                    score=apply_freshness_boost(float(hit.score), article.published_at),
                    snippet=(article.content_clean or article.title)[: self.settings.rag_max_article_snippet_chars],
                    entity_names=list(payload.get("entity_names") or []),
                )
            )

        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:top_k]

    async def retrieve(self, question: str, top_k: int, filters: dict | None = None, use_graph: bool = True) -> RetrievalResult:
        articles = await self.semantic_search(question, top_k=top_k, filters=filters)
        if not articles:
            return RetrievalResult(articles=[], entities=[], graph_edges=[], graph_available=True)

        if not use_graph:
            return RetrievalResult(articles=articles, entities=[], graph_edges=[], graph_available=False)

        graph_service = Neo4jGraphService()
        try:
            graph_context = await graph_service.get_context(
                article_ids=[article.article_id for article in articles],
                max_entities=self.settings.graph_max_entities,
                max_relations=self.settings.graph_max_relations,
            )
            graph_available = True
        except Exception:  # noqa: BLE001
            graph_context = {"entities": [], "edges": []}
            graph_available = False
        finally:
            await graph_service.close()

        return RetrievalResult(
            articles=articles,
            entities=graph_context["entities"],
            graph_edges=[
                RetrievedGraphEdge(
                    from_name=edge["from"],
                    relation=edge["relation"],
                    to_name=edge["to"],
                    source_article_ids=edge["source_article_ids"],
                )
                for edge in graph_context["edges"]
            ],
            graph_available=graph_available,
        )


def apply_freshness_boost(score: float, published_at: datetime | None) -> float:
    if published_at is None:
        return score
    now = datetime.now(UTC)
    published = published_at if published_at.tzinfo else published_at.replace(tzinfo=UTC)
    if published >= now - timedelta(days=7):
        return score + 0.05
    return score
