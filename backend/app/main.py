"""Minimal FastAPI entry point for the Pulseo MVP."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Literal

import psycopg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.schemas import FeedResponse
from app.services.feed import feed_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
# httpx includes full request URLs in its INFO logs. Gemini sends its API key as a
# query parameter, so HTTP client traffic must never be emitted at this level.
logging.getLogger("httpx").setLevel(logging.WARNING)


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["not_configured", "connected", "unavailable"]


def database_status() -> HealthResponse:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return HealthResponse(status="ok", database="not_configured")

    try:
        with psycopg.connect(database_url, connect_timeout=3) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        return HealthResponse(status="ok", database="connected")
    except psycopg.Error:
        return HealthResponse(status="degraded", database="unavailable")


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="Pulseo API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Return API availability and check PostgreSQL only when configured."""
    return await asyncio.to_thread(database_status)


@app.get("/feed", response_model=FeedResponse)
async def feed() -> FeedResponse:
    """Return a small cached feed; the first request collects RSS and calls Gemini once."""
    return await feed_service.get_feed()
