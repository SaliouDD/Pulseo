"""Small synchronous PostgreSQL repository, called off FastAPI's event loop."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.config import DATABASE_URL


@dataclass(frozen=True)
class StoredArticle:
    canonical_key: str
    source_id: str
    source_name: str
    source_language: str
    rss_url: str
    article_url: str
    title: str
    excerpt: str
    published_at: datetime | None


class PulseoRepository:
    def _connect(self) -> psycopg.Connection:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not configured")
        return psycopg.connect(DATABASE_URL, connect_timeout=8, row_factory=dict_row)

    def store_articles(self, articles: list[StoredArticle]) -> dict[str, str]:
        """Upsert source/article data and return canonical key -> persistent event id."""
        event_ids: dict[str, str] = {}
        with self._connect() as connection, connection.cursor() as cursor:
            for article in articles:
                cursor.execute(
                    """
                    insert into sources (id, name, language, rss_url)
                    values (%s, %s, %s, %s)
                    on conflict (id) do update set name = excluded.name, language = excluded.language,
                      rss_url = excluded.rss_url
                    """,
                    (article.source_id, article.source_name, article.source_language, article.rss_url),
                )
                cursor.execute(
                    """
                    insert into events (canonical_key)
                    values (%s)
                    on conflict (canonical_key) do update set updated_at = now()
                    returning id
                    """,
                    (article.canonical_key,),
                )
                event_id = str(cursor.fetchone()["id"])
                event_ids[article.canonical_key] = event_id
                cursor.execute(
                    """
                    insert into articles (source_id, url, original_title, content_excerpt, normalized_hash, published_at, event_id)
                    values (%s, %s, %s, %s, %s, %s, %s)
                    on conflict (url) do update set original_title = excluded.original_title,
                      content_excerpt = excluded.content_excerpt, published_at = excluded.published_at,
                      event_id = excluded.event_id
                    returning id
                    """,
                    (article.source_id, article.article_url, article.title, article.excerpt, article.canonical_key, article.published_at, event_id),
                )
                article_id = str(cursor.fetchone()["id"])
                cursor.execute(
                    """
                    insert into event_sources (event_id, source_id, article_id)
                    values (%s, %s, %s)
                    on conflict do nothing
                    """,
                    (event_id, article.source_id, article_id),
                )
        return event_ids

    def missing_summary_keys(self, language: str, keys: list[str]) -> set[str]:
        if not keys:
            return set()
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                select e.canonical_key
                from events e
                left join event_summaries s on s.event_id = e.id and s.language = %s
                where e.canonical_key = any(%s) and s.event_id is null
                """,
                (language, keys),
            )
            return {str(row["canonical_key"]) for row in cursor.fetchall()}

    def store_summaries(self, language: str, summaries: dict[str, dict[str, Any]], event_ids: dict[str, str]) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            for canonical_key, generated in summaries.items():
                event_id = event_ids.get(canonical_key)
                if not event_id:
                    continue
                cursor.execute(
                    """
                    insert into event_summaries (event_id, language, title, summary, why_it_matters, category, topics, entities)
                    values (%s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (event_id, language) do update set title = excluded.title,
                      summary = excluded.summary, why_it_matters = excluded.why_it_matters,
                      category = excluded.category, topics = excluded.topics, entities = excluded.entities,
                      updated_at = now()
                    """,
                    (
                        event_id,
                        language,
                        str(generated["title"])[:140],
                        str(generated["summary"])[:900],
                        (str(generated.get("why_it_matters"))[:280] if generated.get("why_it_matters") else None),
                        str(generated.get("category") or "Actualité")[:60],
                        [str(topic)[:50] for topic in generated.get("topics", [])[:4]],
                        [str(entity)[:80] for entity in generated.get("entities", [])[:8]],
                    ),
                )

    def feed(self, language: str, limit: int = 6) -> list[dict[str, Any]]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                select e.id, s.title, s.summary, s.why_it_matters, s.category, s.topics, e.importance,
                  max(a.published_at) as published_at,
                  json_agg(json_build_object('id', src.id, 'name', src.name, 'language', src.language,
                    'article_url', a.url) order by src.priority) as sources
                from events e
                join event_summaries s on s.event_id = e.id and s.language = %s
                join event_sources es on es.event_id = e.id
                join sources src on src.id = es.source_id
                join articles a on a.id = es.article_id
                where e.status = 'published'
                group by e.id, s.title, s.summary, s.why_it_matters, s.category, s.topics, e.importance
                order by max(a.published_at) desc nulls last
                limit %s
                """,
                (language, limit),
            )
            return list(cursor.fetchall())


repository = PulseoRepository()
