from datetime import datetime

from pydantic import BaseModel


class ArticleRead(BaseModel):
    id: int
    title: str
    source: str
    url: str
    language: str
    embedding_status: str
    embedding_model: str | None
    embedded_at: datetime | None
    cluster_id: int | None
    clustered_at: datetime | None
    embedding_error: str | None
    published_at: datetime | None
    ingested_at: datetime

    model_config = {"from_attributes": True}


class ArticleDetailRead(BaseModel):
    id: int
    title: str
    content_clean: str
    source: str
    url: str
    published_at: datetime | None
    language: str
    cluster_id: int | None
    entities: list[dict] = []
    related_articles: list[dict] = []

    model_config = {"from_attributes": True}


class ArticleListResponse(BaseModel):
    items: list[ArticleRead]
    page: int
    page_size: int
    total: int
