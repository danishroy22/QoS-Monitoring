"""OpenAI-compatible chat client for Generative AI QoS analysis."""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import Settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when the remote LLM call fails."""


def call_chat_completion(
    *,
    settings: Settings,
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any]:
    """Call an OpenAI-compatible /chat/completions endpoint and parse JSON content."""
    endpoint = settings.openai_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.openai_model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.openai_api_key}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=settings.ai_timeout_seconds) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise LLMError(f"LLM HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise LLMError(f"LLM request failed: {exc}") from exc

    try:
        content = raw["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise LLMError(f"LLM returned unparseable content: {raw}") from exc

    for key in ("summary", "likely_causes", "recommended_actions", "severity"):
        if key not in parsed:
            raise LLMError(f"LLM JSON missing key: {key}")

    if isinstance(parsed["likely_causes"], str):
        parsed["likely_causes"] = [parsed["likely_causes"]]
    if isinstance(parsed["recommended_actions"], str):
        parsed["recommended_actions"] = [parsed["recommended_actions"]]

    parsed["model_provider"] = f"openai:{settings.openai_model}"
    return parsed
