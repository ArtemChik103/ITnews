import logging
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.services.ingestion.schemas import RawArticle

logger = logging.getLogger(__name__)


class RSSSourceClient:
    async def fetch(self) -> list[RawArticle]:
        settings = get_settings()
        articles: list[RawArticle] = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
            for source_url in settings.rss_sources:
                try:
                    response = await client.get(source_url)
                    response.raise_for_status()
                    parsed = feedparser.parse(response.content)
                    hostname = urlparse(source_url).netloc

                    for entry in parsed.entries[:20]:
                        link = entry.get("link", "").strip()
                        title = entry.get("title", "").strip() or "Untitled"
                        if is_promo_spam(title):
                            continue
                        rss_content = _extract_entry_content(entry)

                        full_scraped = await _scrape_full_article(link, client) if link else ""
                        final_content = full_scraped if len(full_scraped) > len(rss_content) else rss_content

                        articles.append(
                            RawArticle(
                                title=title,
                                content_raw=final_content,
                                source=hostname,
                                url=link,
                                published_at=_parse_published_at(entry),
                            )
                        )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Failed to fetch RSS from %s: %s", source_url, exc)

        return [article for article in articles if article.url]


async def _scrape_full_article(url: str, client: httpx.AsyncClient) -> str:
    try:
        res = await client.get(url, timeout=10.0)
        if res.status_code != 200:
            return ""

        html_text = _decode_response_content(res)
        soup = BeautifulSoup(html_text, "html.parser")

        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "iframe", "noscript"]):
            tag.decompose()

        container = (
            soup.find("article")
            or soup.find("main")
            or soup.find("div", class_=re.compile(r"article|content|post-body|entry", re.I))
            or soup
        )

        paragraphs = [p.get_text().strip() for p in container.find_all("p") if len(p.get_text().strip()) > 35]

        if paragraphs:
            return "\n\n".join(paragraphs)
    except Exception:  # noqa: BLE001
        pass
    return ""


def _decode_response_content(res: httpx.Response) -> str:
    content = res.content
    enc = res.encoding
    if enc and enc.lower() not in ("iso-8859-1", "ascii"):
        try:
            return content.decode(enc)
        except Exception:  # noqa: BLE001
            pass

    apparent = getattr(res, "apparent_encoding", None)
    if apparent and apparent.lower() not in ("iso-8859-1", "ascii"):
        try:
            return content.decode(apparent)
        except Exception:  # noqa: BLE001
            pass

    for fallback_enc in ["utf-8", "koi8-r", "windows-1251"]:
        try:
            return content.decode(fallback_enc)
        except Exception:  # noqa: BLE001
            continue

    return res.text


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
        values = [c.get("value", "").strip() for c in entry["content"] if c.get("value")]
        valid = [v for v in values if len(v) > 20]
        if valid:
            return "\n\n".join(valid)
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


PROMO_KEYWORDS = {"coupon", "promo code", "promo codes", "deals for", "off in", "% off", "black friday", "discount code"}


def is_promo_spam(title: str) -> bool:
    lowered = title.lower()
    return any(keyword in lowered for keyword in PROMO_KEYWORDS)

