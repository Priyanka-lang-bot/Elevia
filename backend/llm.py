"""Hosted-LLM client with strict output validation.

Supports Anthropic's Messages API or any OpenAI-compatible Chat Completions API
(OpenAI, Groq, OpenRouter, Gemini's OpenAI endpoint, ...). Uses plain HTTP via
httpx so there is no vendor SDK dependency.

If no provider/key is configured, `complete_json` raises LLMUnavailable and the
agents use their deterministic templates, labelled "template" in the UI.
Nothing here ever fabricates a response that looks like it came from a model.
"""
from __future__ import annotations

import json
import re
from typing import Optional, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from .config import Settings, get_settings

T = TypeVar("T", bound=BaseModel)


class LLMUnavailable(RuntimeError):
    """No LLM configured (mock mode)."""


class LLMError(RuntimeError):
    """The LLM call failed or returned output that failed validation."""


# Optional override used by tests to inject a fake HTTP transport.
_transport: Optional[httpx.BaseTransport] = None


def set_transport(transport: Optional[httpx.BaseTransport]) -> None:
    global _transport
    _transport = transport


def status(settings: Optional[Settings] = None) -> dict:
    s = settings or get_settings()
    if s.llm_enabled:
        return {"mode": "llm", "provider": s.llm_provider, "model": s.llm_model}
    reason = "LLM_PROVIDER is 'mock'" if s.llm_provider == "mock" else "LLM_API_KEY is not set"
    if s.llm_provider not in ("mock", "anthropic", "openai"):
        reason = f"Unknown LLM_PROVIDER '{s.llm_provider}'"
    return {"mode": "mock", "provider": None, "model": None, "reason": reason}


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            raise LLMError("Model reply contained no JSON object")
        text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMError(f"Model reply was not valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise LLMError("Model reply JSON was not an object")
    return data


def _call(system: str, user: str, s: Settings, max_tokens: int) -> str:
    client = httpx.Client(timeout=s.llm_timeout, transport=_transport)
    try:
        if s.llm_provider == "anthropic":
            r = client.post(
                f"{s.llm_base_url}/v1/messages",
                headers={
                    "x-api-key": s.llm_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": s.llm_model,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
            )
            r.raise_for_status()
            body = r.json()
            parts = [b.get("text", "") for b in body.get("content", []) if b.get("type") == "text"]
            return "".join(parts)
        # OpenAI-compatible
        r = client.post(
            f"{s.llm_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {s.llm_api_key}", "content-type": "application/json"},
            json={
                "model": s.llm_model,
                "max_tokens": max_tokens,
                "temperature": 0.3,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            },
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"] or ""
    except httpx.HTTPStatusError as e:
        # Never echo request headers (they contain the key).
        raise LLMError(f"LLM API returned HTTP {e.response.status_code}") from None
    except httpx.HTTPError as e:
        raise LLMError(f"LLM API request failed: {type(e).__name__}") from None
    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise LLMError(f"Unexpected LLM API response shape: {type(e).__name__}") from None
    finally:
        client.close()


def complete_json(system: str, user: str, schema: Type[T], max_tokens: int = 800,
                  settings: Optional[Settings] = None) -> T:
    """Call the LLM and return a validated pydantic object, or raise."""
    s = settings or get_settings()
    if not s.llm_enabled:
        raise LLMUnavailable(status(s).get("reason", "LLM not configured"))
    text = _call(system, user, s, max_tokens)
    data = _extract_json(text)
    try:
        return schema.model_validate(data)
    except ValidationError as e:
        raise LLMError(f"Model output failed validation ({e.error_count()} errors)") from None
