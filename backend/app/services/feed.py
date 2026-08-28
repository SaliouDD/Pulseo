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
import psycopg

from app.ai.gemini import GeminiClient
from app.config import DATABASE_URL, FEED_CACHE_SECONDS
from app.database.repository import StoredArticle, repository
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

LANGUAGE_NAMES = {
    "fr": "français",
    "en": "anglais",
    "ar": "arabe",
    "es": "espagnol",
    "pt": "portugais",
}


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
        self._cache: dict[str, tuple[list[FeedEvent], datetime]] = {}
        self._lock = asyncio.Lock()
        self._gemini = GeminiClient()

    async def get_feed(self, language: str) -> FeedResponse:
        now = datetime.now(UTC)
        cached = self._cache.get(language)
        if cached and now - cached[1] < timedelta(seconds=FEED_CACHE_SECONDS):
            return FeedResponse(items=cached[0], generated_at=cached[1], cached=True)

        async with self._lock:
            cached = self._cache.get(language)
            if cached and now - cached[1] < timedelta(seconds=FEED_CACHE_SECONDS):
                return FeedResponse(items=cached[0], generated_at=cached[1], cached=True)
            events = await self.refresh(language)
            generated_at = datetime.now(UTC)
            self._cache[language] = (events, generated_at)
            return FeedResponse(items=events, generated_at=generated_at, cached=False)

    async def refresh(self, language: str) -> list[FeedEvent]:
        articles = [article for source_articles in await asyncio.gather(*(collect_source(source) for source in SOURCES)) for article in source_articles]
        articles.sort(key=lambda article: article.published_at or datetime.min.replace(tzinfo=UTC), reverse=True)
        articles = articles[:6]
        target_language = LANGUAGE_NAMES.get(language, language)

        if DATABASE_URL:
            try:
                event_ids = await asyncio.to_thread(
                    repository.store_articles,
                    [
                        StoredArticle(
                            canonical_key=article.id,
                            source_id=article.source.id,
                            source_name=article.source.name,
                            source_language=article.source.language,
                            rss_url=article.source.rss_url,
                            article_url=article.url,
                            title=article.title,
                            excerpt=article.excerpt,
                            published_at=article.published_at,
                        )
                        for article in articles
                    ],
                )
                missing_keys = await asyncio.to_thread(repository.missing_summary_keys, language, list(event_ids))
                if missing_keys:
                    summaries = await self._gemini.summarize(
                        [
                            {"id": article.id, "source": article.source.name, "title": article.title, "excerpt": article.excerpt}
                            for article in articles if article.id in missing_keys
                        ],
                        target_language,
                    )
                    if summaries:
                        await asyncio.to_thread(repository.store_summaries, language, summaries, event_ids)
                stored_events = await asyncio.to_thread(repository.feed, language)
                if stored_events:
                    logger.info("Loaded %s persistent %s summaries from Supabase", len(stored_events), language)
                    return [self._event_from_row(row) for row in stored_events]
            except (psycopg.Error, RuntimeError) as error:
                logger.warning("Supabase persistence unavailable; using temporary feed: %s", error)

        summaries = await self._gemini.summarize(
            [{"id": article.id, "source": article.source.name, "title": article.title, "excerpt": article.excerpt} for article in articles],
            target_language,
        )
        events = [self._to_event(article, summaries.get(article.id)) for article in articles]
        logger.info("Feed refreshed with %s events in %s", len(events), language)
        return events

    @staticmethod
    def _event_from_row(row: dict) -> FeedEvent:
        return FeedEvent(
            id=str(row["id"]),
            title=str(row["title"]),
            summary=str(row["summary"]),
            why_it_matters=row["why_it_matters"],
            category=str(row["category"]),
            topics=list(row["topics"] or []),
            importance=float(row["importance"]),
            published_at=row["published_at"],
            sources=[Source(**source) for source in row["sources"]],
        )

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
