"""AI client wrapper — supports OpenAI, Groq, and Gemini via OpenAI-compatible endpoints."""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel
from structlog import get_logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = get_logger(__name__)


# Provider configs
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = "gemini-2.0-flash"


def detect_provider(api_key: str) -> str:
    """Auto-detect provider from API key prefix."""
    if api_key.startswith("sk-"):
        return "openai"
    if api_key.startswith("gsk_"):
        return "groq"
    return "gemini"


class AIClient:
    """Wrapper around OpenAI SDK that supports OpenAI and Gemini.

    Usage::

        client = AIClient(api_key="...")  # auto-detects provider
        result = await client.structured(
            system="You are an expert analyst.",
            user="Analyze this document...",
            response_model=TechnologyList,
        )
    """

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        base_url: str | None = None,
        max_retries: int = 3,
    ) -> None:
        provider = detect_provider(api_key)

        if provider == "groq":
            self.model = GROQ_MODEL  # Always use Groq model
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url or GROQ_BASE_URL,
                max_retries=max_retries,
            )
            logger.info("ai_client_init", provider="groq", model=self.model)
        elif provider == "gemini":
            # Ignore any passed model for Gemini, use our default
            self.model = GEMINI_MODEL
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url or GEMINI_BASE_URL,
                max_retries=max_retries,
            )
            logger.info("ai_client_init", provider="gemini", model=self.model)
        else:
            self.model = model or "gpt-4o-mini"
            self._client = AsyncOpenAI(api_key=api_key, max_retries=max_retries)
            logger.info("ai_client_init", provider="openai", model=self.model)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def chat(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.1,
        response_format: type | None = None,
    ) -> str:
        """Send a chat completion and return the text response."""
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        if response_format is not None and issubclass(response_format, BaseModel):
            # Use json_object with schema description (works across all providers)
            kwargs["response_format"] = {"type": "json_object"}
            schema_str = json.dumps(response_format.model_json_schema(), indent=2)
            messages[1]["content"] += (
                f"\n\nYou MUST respond with a valid JSON object matching this schema:\n{schema_str}\n\n"
                "No markdown fences, no extra text."
            )
        elif response_format is not None:
            kwargs["response_format"] = {"type": "json_object"}
            messages[1]["content"] += (
                "\n\nRespond ONLY with a valid JSON object. "
                "No markdown fences or extra text."
            )

        response = await self._client.chat.completions.create(**kwargs)
        text = response.choices[0].message.content or ""
        logger.debug("ai_chat_response", model=self.model, chars=len(text))
        return text

    async def structured(
        self,
        system: str,
        user: str,
        response_model: type[BaseModel],
        *,
        temperature: float = 0.1,
    ) -> BaseModel:
        """Request a structured JSON output parsed into *response_model*."""
        text = await self.chat(
            system=system,
            user=user,
            temperature=temperature,
            response_format=response_model,
        )
        # Clean up potential markdown fences
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("ai_structured_parse_failed", text=text[:200])
            return response_model()

        return response_model.model_validate(data)

    async def close(self) -> None:
        await self._client.close()
