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
