"""Small Gemini REST client. The API key never leaves the backend."""

import json
import logging
from typing import Any

import httpx

from app.ai.prompts import build_batch_prompt
from app.config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)


class GeminiClient:
    async def summarize(self, articles: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
        """Summarise a batch, returning an empty mapping when Gemini is unavailable."""
        if not GEMINI_API_KEY:
            logger.warning("Gemini is not configured; RSS descriptions will be used")
            return {}

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": build_batch_prompt(articles)}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        try:
            async with httpx.AsyncClient(timeout=25) as client:
                response = await client.post(url, params={"key": GEMINI_API_KEY}, json=payload)
                response.raise_for_status()
            parts = response.json()["candidates"][0]["content"]["parts"]
            result = json.loads("".join(part.get("text", "") for part in parts))
            events = result.get("events", [])
            if not isinstance(events, list):
                raise ValueError("Gemini response has no events list")
            logger.info("Gemini summarised %s RSS articles in one request", len(events))
            return {str(event["id"]): event for event in events if isinstance(event, dict) and event.get("id")}
        except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError) as error:
            logger.warning("Gemini summary failed: %s", error)
            return {}
