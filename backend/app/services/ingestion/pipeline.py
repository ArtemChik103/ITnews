import logging
from collections.abc import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.services.ingestion.preprocess import clean_html, detect_language, normalize_text
from app.services.ingestion.sources import NewsAPIClient, RSSSourceClient

logger = logging.getLogger(__name__)


class IngestionPipeline:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.rss_client = RSSSourceClient()
        self.api_client = NewsAPIClient()

    async def run(self) -> dict:
        raw_articles = await self.rss_client.fetch()
        raw_articles.extend(await self.api_client.fetch())

        saved = 0
        duplicates = 0
        errors = 0

        for raw in raw_articles:
            try:
                existing = await self.session.scalar(select(Article).where(Article.url == raw.url))
                if existing is not None:
                    duplicates += 1
                    continue

                content_clean = clean_html(raw.content_raw)
                article = Article(
                    title=raw.title,
                    content_raw=raw.content_raw,
                    content_clean=content_clean,
                    content_normalized=normalize_text(content_clean),
                    source=raw.source,
                    url=raw.url,
                    published_at=raw.published_at,
                    language=detect_language(content_clean or raw.title),
                    embedding_status="pending",
                    embedding_attempts=0,
                )
                self.session.add(article)
                saved += 1
            except Exception as exc:  # noqa: BLE001
                logger.exception("Failed to ingest article %s: %s", raw.url, exc)
                errors += 1

        await self.session.commit()
        return {"fetched": len(raw_articles), "saved": saved, "duplicates": duplicates, "errors": errors}

    async def list_articles(self) -> Sequence[Article]:
        result = await self.session.scalars(select(Article).order_by(desc(Article.ingested_at)).limit(50))
        return result.all()

    async def get_article(self, article_id: int) -> Article | None:
        return await self.session.get(Article, article_id)
