from datetime import datetime

from pydantic import BaseModel


class ArticleRead(BaseModel):
    id: int
    title: str
    source: str
    url: str
    language: str
    published_at: datetime | None
    ingested_at: datetime

    model_config = {"from_attributes": True}
