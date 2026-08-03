from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
import numpy as np
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.article import Article


@dataclass(slots=True)
class ScoredPoint:
    id: int
    score: float
    payload: dict


@dataclass(slots=True)
class Record:
    id: int
    payload: dict
    vector: list[float]


class VectorStoreService:
    """PostgreSQL + NumPy backed vector store replacing Qdrant."""

    async def close(self) -> None:
        pass

    async def ensure_collection(self) -> None:
        pass

    async def upsert_article_embedding(self, article_id: int, embedding: list[float], payload: dict) -> None:
        async with SessionLocal() as session:
            article = await session.get(Article, article_id)
            if article:
                article.embedding_data = json.dumps(embedding)
                await session.commit()

    async def search(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: dict | None = None,
    ) -> list[ScoredPoint]:
        async with SessionLocal() as session:
            stmt = select(Article).where(Article.embedding_data.is_not(None))

            if filters:
                source = filters.get("source")
                sources = filters.get("sources")
                if source:
                    stmt = stmt.where(Article.source == source)
                elif sources:
                    stmt = stmt.where(Article.source.in_(sources))

                language = filters.get("language")
                if language:
                    stmt = stmt.where(Article.language == language)

                date_from = filters.get("date_from")
                if date_from:
                    try:
                        dt_from = datetime.fromisoformat(date_from)
                    except ValueError:
                        dt_from = datetime.strptime(date_from, "%Y-%m-%d")
                    stmt = stmt.where(Article.published_at >= dt_from)

                date_to = filters.get("date_to")
                if date_to:
                    try:
                        dt_to = datetime.fromisoformat(date_to)
                    except ValueError:
                        dt_to = datetime.strptime(date_to, "%Y-%m-%d")
                    dt_to = dt_to.replace(hour=23, minute=59, second=59)
                    stmt = stmt.where(Article.published_at <= dt_to)

            res = await session.scalars(stmt)
            articles = list(res.all())

            if not articles:
                return []

            q_vec = np.array(query_embedding, dtype=np.float32)
            q_norm = np.linalg.norm(q_vec)
            if q_norm == 0:
                return []

            scored_points: list[ScoredPoint] = []
            for article in articles:
                if not article.embedding_data:
                    continue
                try:
                    vec = np.array(json.loads(article.embedding_data), dtype=np.float32)
                    v_norm = np.linalg.norm(vec)
                    if v_norm == 0:
                        continue
                    score = float(np.dot(q_vec, vec) / (q_norm * v_norm))
                    payload = {
                        "article_id": str(article.id),
                        "title": article.title,
                        "source": article.source,
                        "url": article.url,
                        "language": article.language,
                        "published_at": article.published_at.isoformat() if article.published_at else None,
                        "cluster_id": article.cluster_id,
                        "entity_names": [],
                    }
                    scored_points.append(ScoredPoint(id=article.id, score=score, payload=payload))
                except Exception:  # noqa: BLE001
                    continue

            scored_points.sort(key=lambda p: p.score, reverse=True)
            return scored_points[:top_k]

    async def update_cluster_metadata(self, article_id: int, cluster_id: int | None) -> None:
        async with SessionLocal() as session:
            article = await session.get(Article, article_id)
            if article:
                article.cluster_id = cluster_id
                await session.commit()

    async def delete_article(self, article_id: int) -> None:
        async with SessionLocal() as session:
            article = await session.get(Article, article_id)
            if article:
                article.embedding_data = None
                await session.commit()

    async def fetch_ready_points(self) -> list[Record]:
        async with SessionLocal() as session:
            stmt = select(Article).where(Article.embedding_data.is_not(None))
            res = await session.scalars(stmt)
            articles = list(res.all())

            records: list[Record] = []
            for article in articles:
                if not article.embedding_data:
                    continue
                try:
                    vec = json.loads(article.embedding_data)
                    records.append(Record(
                        id=article.id,
                        payload={"cluster_id": article.cluster_id},
                        vector=vec,
                    ))
                except Exception:  # noqa: BLE001
                    continue
            return records
