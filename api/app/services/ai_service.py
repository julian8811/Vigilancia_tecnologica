"""Lightweight AI client for API-side AI calls (search strategy generation).

Uses httpx to call OpenAI/Gemini-compatible endpoints. No external
openai dependency — keeps the API lightweight.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from structlog import get_logger

from app.core.config import settings

logger = get_logger(__name__)

# Gemini uses an OpenAI-compatible endpoint
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
OPENAI_BASE_URL = "https://api.openai.com/v1"


def _resolve_config():
    key = settings.OPENAI_API_KEY or settings.GEMINI_API_KEY or ""
    if not key:
        return None, None, None, None

    if key.startswith("sk-"):
        model = "gpt-4o-mini"
        base_url = OPENAI_BASE_URL
    else:
        model = "gemini-2.0-flash"
        base_url = GEMINI_BASE_URL

    return key, model, base_url


SEARCH_STRATEGY_PROMPT = """You are an expert in academic literature search and bibliometrics. Given a research topic and description, generate a comprehensive search strategy for academic databases (OpenAlex, Semantic Scholar).

Return a JSON object with these fields:
- keywords_en: array of English keywords (5-10 most relevant terms)
- keywords_es: array of Spanish keywords if the topic suggests Spanish content (3-5 terms, empty array if not relevant)
- boolean_queries: array of 2-4 OpenAlex-compatible boolean search queries combining keywords with AND/OR operators. Use double quotes for multi-word terms. Example: "machine learning" AND (cancer OR oncology)
- synonyms: array of synonym or related terms not already in the keywords (5-10 terms)
- sources_recommended: array of sources to use from: ["openalex", "semantic_scholar", "lens", "web"]

IMPORTANT: Return ONLY valid JSON, no markdown, no explanation."""


async def generate_search_strategy(topic: str, description: str = "") -> dict[str, Any]:
    key, model, base_url = _resolve_config()
    if not key or not model or not base_url:
        logger.warning("ai_generate_skip_no_key")
        return {}

    prompt = f"Topic: {topic}"
    if description:
        prompt += f"\nDescription: {description}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": SEARCH_STRATEGY_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1000,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)

            logger.info("ai_search_strategy_generated", topic=topic[:100])
            return result

    except Exception as exc:
        logger.exception("ai_search_strategy_failed", topic=topic[:100], error=str(exc))
        return {}


CLASSIFY_PROMPT = """Classify each document into one of these types based on its title and abstract:
paper, patent, report, thesis, book, dataset, webpage, news, other

Return a JSON array of [document_id, type] pairs. Example:
[["id1","paper"],["id2","report"],["id3","news"]]

IMPORTANT: Return ONLY the JSON array, no explanation."""


async def classify_document_batch(
    docs: list[tuple[str, str, str]],
) -> list[tuple[str, str]]:
    """Classify documents by type using AI. Each doc is (id, abstract, title)."""
    key, model, base_url = _resolve_config()
    if not key or not model or not base_url:
        return [(doc_id, "other") for doc_id, _, _ in docs]

    lines = []
    for doc_id, abstract, title in docs[:30]:
        text = (abstract or title)[:300]
        lines.append(f"  [{doc_id}] {text}")
    doc_text = "\n".join(lines)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": CLASSIFY_PROMPT},
                        {"role": "user", "content": f"Documents:\n{doc_text}"},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1000,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)
            return [(str(r[0]), str(r[1])) for r in result if len(r) >= 2]

    except Exception as exc:
        logger.exception("classify_documents_failed", error=str(exc))
        return [(doc_id, "other") for doc_id, _, _ in docs]
