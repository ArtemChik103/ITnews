from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import feedparser
import httpx

from app.core.config import get_settings
from app.services.ingestion.schemas import RawArticle


class RSSSourceClient:
    async def fetch(self) -> list[RawArticle]:
        settings = get_settings()
        articles: list[RawArticle] = []

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            for source_url in settings.rss_sources:
                response = await client.get(source_url)
                response.raise_for_status()
                parsed = feedparser.parse(response.text)
                hostname = urlparse(source_url).netloc
                for entry in parsed.entries:
                    articles.append(
                        RawArticle(
                            title=entry.get("title", "").strip() or "Untitled",
                            content_raw=_extract_entry_content(entry),
                            source=hostname,
                            url=entry.get("link", "").strip(),
                            published_at=_parse_published_at(entry),
                        )
                    )
        return [article for article in articles if article.url]


class NewsAPIClient:
    async def fetch(self) -> list[RawArticle]:
        settings = get_settings()
        if not settings.enable_news_api or not settings.news_api_key:
            return []

        params = {
            "q": settings.news_api_query,
            "apiKey": settings.news_api_key,
            "pageSize": 20,
            "sortBy": "publishedAt",
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(settings.news_api_url, params=params)
            response.raise_for_status()
            payload = response.json()

        articles = []
        for item in payload.get("articles", []):
            articles.append(
                RawArticle(
                    title=(item.get("title") or "").strip() or "Untitled",
                    content_raw=(item.get("content") or item.get("description") or "").strip(),
                    source=((item.get("source") or {}).get("name") or "newsapi").strip(),
                    url=(item.get("url") or "").strip(),
                    published_at=_parse_iso_datetime(item.get("publishedAt")),
                )
            )
        return [article for article in articles if article.url]


def _extract_entry_content(entry: dict) -> str:
    if entry.get("content"):
        return (entry["content"][0].get("value") or "").strip()
    return (entry.get("summary") or entry.get("description") or "").strip()


def _parse_published_at(entry: dict) -> datetime | None:
    published = entry.get("published") or entry.get("updated")
    if not published:
        return None
    try:
        return parsedate_to_datetime(published)
    except (TypeError, ValueError, IndexError):
        return None


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
