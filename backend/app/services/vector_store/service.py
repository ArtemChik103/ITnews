import asyncio
from datetime import datetime

import httpx
from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.core.config import get_settings


class VectorStoreService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = QdrantClient(host=self.settings.qdrant_host, port=self.settings.qdrant_port)

    async def close(self) -> None:
        await asyncio.to_thread(self.client.close)

    async def ensure_collection(self) -> None:
        await asyncio.to_thread(self._ensure_collection_sync)

    def _ensure_collection_sync(self) -> None:
        collections = self.client.get_collections().collections
        if any(collection.name == self.settings.qdrant_collection for collection in collections):
            return
        self.client.create_collection(
            collection_name=self.settings.qdrant_collection,
            vectors_config=models.VectorParams(
                size=self.settings.embedding_dimension,
                distance=models.Distance.COSINE,
            ),
        )

    async def upsert_article_embedding(self, article_id: int, embedding: list[float], payload: dict) -> None:
        await self.ensure_collection()
        await asyncio.to_thread(
            self.client.upsert,
            collection_name=self.settings.qdrant_collection,
            points=[
                models.PointStruct(
                    id=article_id,
                    vector=embedding,
                    payload=payload,
                )
            ],
            wait=True,
        )

    async def search(
        self,
        query_embedding: list[float],
        top_k: int,
        filters: dict | None = None,
    ) -> list[models.ScoredPoint]:
        await self.ensure_collection()
        query_filter = build_qdrant_filter(filters or {})
        return await asyncio.to_thread(
            self.client.search,
            collection_name=self.settings.qdrant_collection,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

    async def update_cluster_metadata(self, article_id: int, cluster_id: int | None) -> None:
        await self.ensure_collection()
        await asyncio.to_thread(
            self.client.set_payload,
            collection_name=self.settings.qdrant_collection,
            payload={"cluster_id": cluster_id},
            points=[article_id],
            wait=True,
        )

    async def delete_article(self, article_id: int) -> None:
        await self.ensure_collection()
        await asyncio.to_thread(
            self.client.delete,
            collection_name=self.settings.qdrant_collection,
            points_selector=models.PointIdsList(points=[article_id]),
            wait=True,
        )

    async def fetch_ready_points(self) -> list[models.Record]:
        await self.ensure_collection()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"http://{self.settings.qdrant_host}:{self.settings.qdrant_port}/collections/{self.settings.qdrant_collection}/points/scroll",
                json={
                    "limit": 10000,
                    "with_payload": True,
                    "with_vector": True,
                },
            )
            response.raise_for_status()
            payload = response.json()

        points = payload.get("result", {}).get("points", [])
        return [
            models.Record(
                id=point["id"],
                payload=point.get("payload") or {},
                vector=point.get("vector"),
            )
            for point in points
            if point.get("vector")
        ]


def build_qdrant_filter(filters: dict) -> models.Filter | None:
    conditions: list[models.FieldCondition] = []
    should_conditions: list[models.FieldCondition] = []

    source = filters.get("source")
    sources = filters.get("sources")
    if source:
        conditions.append(models.FieldCondition(key="source", match=models.MatchValue(value=source)))
    elif sources:
        should_conditions.extend([models.FieldCondition(key="source", match=models.MatchValue(value=item)) for item in sources])

    language = filters.get("language")
    if language:
        conditions.append(models.FieldCondition(key="language", match=models.MatchValue(value=language)))

    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    if date_from or date_to:
        conditions.append(
            models.FieldCondition(
                key="published_at_ts",
                range=models.Range(
                    gte=to_timestamp(date_from) if date_from else None,
                    lte=to_timestamp(date_to, end_of_day=True) if date_to else None,
                ),
            )
        )

    if not conditions and not should_conditions:
        return None
    return models.Filter(must=conditions, should=should_conditions or None)


def to_timestamp(value: datetime | str, end_of_day: bool = False) -> int:
    if isinstance(value, str):
        parsed = datetime.fromisoformat(f"{value}T23:59:59" if end_of_day else f"{value}T00:00:00")
    else:
        parsed = value
    return int(parsed.timestamp())
