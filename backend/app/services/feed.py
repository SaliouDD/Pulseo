"""RSS collection and lightweight event feed assembly for the first Pulseo milestone."""

import asyncio
import hashlib
import html
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from app.ai.gemini import GeminiClient
from app.config import FEED_CACHE_SECONDS
from app.schemas import FeedEvent, FeedResponse, Source

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RssSource:
    id: str
    name: str
    language: str
    rss_url: str


SOURCES = (
    RssSource("france24", "France 24", "fr", "https://www.france24.com/fr/rss"),
    RssSource("bbc", "BBC News", "en", "https://feeds.bbci.co.uk/news/world/rss.xml"),
)


@dataclass(frozen=True)
class Article:
    id: str
    title: str
    excerpt: str
    url: str
    published_at: datetime | None
    source: RssSource


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def parse_date(entry: dict) -> datetime | None:
    raw_date = entry.get("published") or entry.get("updated")
    if not raw_date:
        return None
    try:
        parsed = parsedate_to_datetime(raw_date)
        return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None


async def collect_source(source: RssSource) -> list[Article]:
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            response = await client.get(source.rss_url, headers={"User-Agent": "PulseoMVP/0.1"})
            response.raise_for_status()
        parsed = feedparser.parse(response.content)
        articles: list[Article] = []
        for entry in parsed.entries[:4]:
            title, url = clean_text(entry.get("title", "")), entry.get("link", "")
            if not title or not url:
                continue
            digest = hashlib.sha256(f"{source.id}:{url}".encode()).hexdigest()[:16]
            articles.append(Article(digest, title, clean_text(entry.get("summary", ""))[:1800], url, parse_date(entry), source))
        logger.info("Collected %s articles from %s", len(articles), source.name)
        return articles
    except (httpx.HTTPError, ValueError) as error:
        logger.warning("RSS collection failed for %s: %s", source.name, error)
        return []


class FeedService:
    def __init__(self) -> None:
        self._cache: list[FeedEvent] = []
        self._generated_at: datetime | None = None
        self._lock = asyncio.Lock()
        self._gemini = GeminiClient()

    async def get_feed(self) -> FeedResponse:
        now = datetime.now(UTC)
        if self._generated_at and now - self._generated_at < timedelta(seconds=FEED_CACHE_SECONDS):
            return FeedResponse(items=self._cache, generated_at=self._generated_at, cached=True)

        async with self._lock:
            if self._generated_at and now - self._generated_at < timedelta(seconds=FEED_CACHE_SECONDS):
                return FeedResponse(items=self._cache, generated_at=self._generated_at, cached=True)
            await self.refresh()
            return FeedResponse(items=self._cache, generated_at=self._generated_at or now, cached=False)

    async def refresh(self) -> None:
        articles = [article for source_articles in await asyncio.gather(*(collect_source(source) for source in SOURCES)) for article in source_articles]
        articles.sort(key=lambda article: article.published_at or datetime.min.replace(tzinfo=UTC), reverse=True)
        articles = articles[:6]
        summaries = await self._gemini.summarize(
            [{"id": article.id, "source": article.source.name, "title": article.title, "excerpt": article.excerpt} for article in articles]
        )
        self._cache = [self._to_event(article, summaries.get(article.id)) for article in articles]
        self._generated_at = datetime.now(UTC)
        logger.info("Feed refreshed with %s events", len(self._cache))

    @staticmethod
    def _to_event(article: Article, generated: dict | None) -> FeedEvent:
        fallback_summary = article.excerpt or article.title
        def text(field: str, fallback: str, limit: int) -> str:
            value = str((generated or {}).get(field) or fallback).strip()
            return value[:limit]

        try:
            importance = float((generated or {}).get("importance", 0.5))
        except (TypeError, ValueError):
            importance = 0.5

        return FeedEvent(
            id=article.id,
            title=text("title", article.title, 140),
            summary=text("summary", fallback_summary, 900),
            why_it_matters=text("why_it_matters", "", 280) or None,
            category=text("category", "Actualité", 60),
            topics=[str(topic)[:50] for topic in (generated or {}).get("topics", [])[:4]],
            importance=max(0, min(importance, 1)),
            published_at=article.published_at,
            sources=[Source(id=article.source.id, name=article.source.name, language=article.source.language, article_url=article.url)],
        )


feed_service = FeedService()
