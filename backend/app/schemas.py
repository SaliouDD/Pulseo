from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class Source(BaseModel):
    id: str
    name: str
    language: str
    article_url: HttpUrl


class FeedEvent(BaseModel):
    id: str
    title: str = Field(min_length=1, max_length=140)
    summary: str = Field(min_length=1, max_length=900)
    why_it_matters: str | None = Field(default=None, max_length=280)
    category: str = "Actualité"
    topics: list[str] = Field(default_factory=list)
    importance: float = Field(default=0.5, ge=0, le=1)
    published_at: datetime | None = None
    sources: list[Source]


class FeedResponse(BaseModel):
    items: list[FeedEvent]
    generated_at: datetime
    cached: bool
