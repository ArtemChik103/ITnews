from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class RawArticle:
    title: str
    content_raw: str
    source: str
    url: str
    published_at: datetime | None
