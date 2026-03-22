from __future__ import annotations

from datetime import datetime, timezone
from math import floor, sqrt

import hdbscan
import numpy as np
from sklearn.cluster import KMeans
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.article import Article
from app.services.vector_store.service import VectorStoreService


class ClusteringService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()

    async def recluster(self) -> dict:
        vector_store = VectorStoreService()
        try:
            points = await vector_store.fetch_ready_points()
            if not points:
                return {"algorithm": "none", "clustered": 0}

            article_ids = [int(point.id) for point in points]
            matrix = np.asarray([point.vector for point in points], dtype=np.float32)
            labels, algorithm = cluster_vectors(
                matrix=matrix,
                hdbscan_threshold=self.settings.clustering_hdbscan_threshold,
                min_cluster_size=self.settings.clustering_min_cluster_size,
            )

            now = datetime.now(timezone.utc)
            articles = await self.session.scalars(select(Article).where(Article.id.in_(article_ids)))
            article_map = {article.id: article for article in articles}

            for article_id, cluster_id in zip(article_ids, labels, strict=True):
                article = article_map.get(article_id)
                if article is None:
                    continue
                article.cluster_id = int(cluster_id)
                article.clustered_at = now
                await vector_store.update_cluster_metadata(article_id=article_id, cluster_id=int(cluster_id))

            await self.session.commit()
            return {"algorithm": algorithm, "clustered": len(article_ids)}
        finally:
            await vector_store.close()

    async def list_clusters(self) -> list[dict]:
        articles = await self.session.scalars(
            select(Article).where(Article.cluster_id.is_not(None), Article.cluster_id != -1).order_by(Article.cluster_id, Article.published_at)
        )
        clusters: dict[int, list[Article]] = {}
        for article in articles:
            clusters.setdefault(article.cluster_id, []).append(article)

        summaries = []
        for cluster_id, items in sorted(clusters.items(), key=lambda item: len(item[1]), reverse=True):
            top_sources = sorted({article.source for article in items})[:3]
            sample_articles = [
                {
                    "article_id": article.id,
                    "title": article.title,
                    "source": article.source,
                    "url": article.url,
                    "published_at": article.published_at,
                    "cluster_id": article.cluster_id,
                    "score": 1.0,
                }
                for article in items[:3]
            ]
            summaries.append(
                {
                    "cluster_id": cluster_id,
                    "size": len(items),
                    "sample_articles": sample_articles,
                    "top_sources": top_sources,
                }
            )
        return summaries


def cluster_vectors(matrix: np.ndarray, hdbscan_threshold: int, min_cluster_size: int) -> tuple[list[int], str]:
    count = len(matrix)
    if count == 0:
        return [], "none"
    if count == 1:
        return [0], "single"
    if count < hdbscan_threshold:
        clusters = max(2, min(10, floor(sqrt(count / 2))))
        model = KMeans(n_clusters=min(clusters, count), n_init="auto", random_state=42)
        return model.fit_predict(matrix).astype(int).tolist(), "kmeans"

    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric="euclidean")
    labels = clusterer.fit_predict(matrix).astype(int).tolist()
    return labels, "hdbscan"
