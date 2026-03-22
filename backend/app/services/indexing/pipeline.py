from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.article import Article
from app.services.embeddings.service import EmbeddingService
from app.services.graph.neo4j import Neo4jGraphService
from app.services.vector_store.service import VectorStoreService

indexed_since_recluster = 0


class IndexingPipeline:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.embedding_service = EmbeddingService()

    async def run(self) -> dict:
        global indexed_since_recluster
        articles = await self.session.scalars(
            select(Article).where(
                or_(Article.embedding_status == "pending", Article.embedding_status == "failed"),
                Article.embedding_attempts < self.settings.embedding_max_retries,
            ).order_by(Article.ingested_at).limit(100)
        )
        pending = list(articles)
        vector_store = VectorStoreService()
        graph = Neo4jGraphService()
        indexed = 0
        skipped = 0
        failed = 0

        try:
            await vector_store.ensure_collection()
            for article in pending:
                article.embedding_attempts += 1
                result = await self.embedding_service.generate(
                    article_id=article.id,
                    title=article.title,
                    content_clean=article.content_clean,
                    language=article.language,
                )
                article.embedding_status = result.status
                article.embedding_model = result.embedding_model
                article.embedding_error = result.error

                if result.status == "ready" and result.embedding:
                    article.embedded_at = datetime.now(UTC)
                    payload = await build_qdrant_payload(graph=graph, article=article)
                    await vector_store.upsert_article_embedding(
                        article_id=article.id,
                        embedding=result.embedding,
                        payload=payload,
                    )
                    indexed += 1
                elif result.status == "skipped":
                    skipped += 1
                else:
                    failed += 1

            await self.session.commit()
        finally:
            await vector_store.close()
            await graph.close()

        indexed_since_recluster += indexed
        return {
            "selected": len(pending),
            "indexed": indexed,
            "skipped": skipped,
            "failed": failed,
            "trigger_recluster": indexed_since_recluster >= 100,
        }


async def build_qdrant_payload(graph: Neo4jGraphService, article: Article) -> dict:
    entity_names = []
    try:
        entity_names = await graph.get_article_entities(article.id)
    except Exception:  # noqa: BLE001
        entity_names = []

    return {
        "article_id": str(article.id),
        "title": article.title,
        "source": article.source,
        "url": article.url,
        "language": article.language,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "published_at_ts": int(article.published_at.timestamp()) if article.published_at else None,
        "cluster_id": article.cluster_id,
        "entity_names": entity_names,
        "has_entities": bool(entity_names),
    }
