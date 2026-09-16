"""OpenAI-compatible Hy3 provider with exponential-backoff retry.

Uses the ``openai`` client against a configurable base URL, which makes Hy3
(the default provider) swappable with any OpenAI-compatible endpoint. Records
latency, retry count, usage, and error metadata for provenance (EXT-08).
"""
from __future__ import annotations

import random
import time
from typing import Any

from openai import OpenAI

from src.llm.base import BaseLLMProvider, ProviderResult


def is_non_retryable(error: str) -> bool:
    """Quota / auth failures will not recover by waiting."""
    text = error.lower()
    return (
        "401008" in error
        or "error code: 402" in text
        or "error code: 401" in text
        or "quota" in text
        or "unauthorized" in text
    )


class Hy3Provider(BaseLLMProvider):
    name = "hy3"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
        max_retries: int = 3,
        retry_backoff_base: float = 2.0,
        empty_content_fallback_effort: str | None = None,
        client: Any = None,
    ) -> None:
        if not api_key:
            raise ValueError("Hy3Provider requires a non-empty api_key.")
        self.model = model or ""
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_base = retry_backoff_base
        self._empty_content_fallback_effort = empty_content_fallback_effort
        # max_retries=0 disables the SDK's own retry so our backoff owns retries.
        self._client = client or OpenAI(
            api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0
        )

    def _attempt(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        extra_body: dict[str, Any],
    ) -> tuple[str, str | None, dict[str, Any], str | None, int]:
        """One full try/backoff cycle. Returns (content, reasoning, usage, error, attempts)."""
        last_error: str | None = None
        attempts = 0
        for attempt in range(self._max_retries + 1):
            attempts = attempt
            try:
                kwargs: dict[str, Any] = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if extra_body:
                    kwargs["extra_body"] = extra_body
                resp = self._client.chat.completions.create(**kwargs)
                message = resp.choices[0].message
                content = message.content or ""
                # Hy3 exposes the hidden chain-of-thought via reasoning_content;
                # keep it so the trace is preserved in the raw record (MathXRay).
                reasoning = getattr(message, "reasoning_content", None) or None
                usage: dict[str, Any] = {}
                if getattr(resp, "usage", None) is not None:
                    usage = {
                        "prompt_tokens": resp.usage.prompt_tokens,
                        "completion_tokens": resp.usage.completion_tokens,
                        "total_tokens": resp.usage.total_tokens,
                    }
                return content, reasoning, usage, None, attempts
            except Exception as exc:  # noqa: BLE001 - record and retry any transport error
                last_error = f"{type(exc).__name__}: {exc}"
                if is_non_retryable(last_error) or attempt >= self._max_retries:
                    break
                delay = self._backoff_base**attempt + random.uniform(0, 0.5)
                time.sleep(delay)
        return "", None, {}, last_error, attempts

    def complete(self, messages: list[dict[str, str]], **gen_cfg: Any) -> ProviderResult:
        cfg = dict(gen_cfg)
        temperature = cfg.pop("temperature", 0.0)
        max_tokens = cfg.pop("max_tokens", 4096)
        extra_body: dict[str, Any] = {}
        if "reasoning_effort" in cfg:
            extra_body["reasoning_effort"] = cfg.pop("reasoning_effort")

        start = time.perf_counter()
        content, reasoning, usage, error, attempts = self._attempt(
            messages, temperature, max_tokens, extra_body
        )

        # Deep-thinking models can spend the whole budget on reasoning_content and
        # return an empty content. When that happens, retry once with a lower
        # reasoning effort to elicit the structured final answer. The fallback is
        # marked in usage so the trace records what actually happened.
        fallback = self._empty_content_fallback_effort
        if error is None and not content and reasoning and fallback:
            fb_extra = dict(extra_body)
            fb_extra["reasoning_effort"] = fallback
            fb_content, fb_reasoning, fb_usage, fb_error, fb_attempts = self._attempt(
                messages, temperature, max_tokens, fb_extra
            )
            # +1 accounts for the extra fallback call itself; fb_attempts covers
            # any transport retries inside the fallback cycle.
            attempts += 1 + fb_attempts
            usage = {**usage, "empty_content_fallback": fallback}
            if fb_error is None and fb_content:
                content, reasoning, usage = fb_content, fb_reasoning, fb_usage
                usage["empty_content_fallback"] = fallback

        latency_ms = (time.perf_counter() - start) * 1000.0
        return ProviderResult(
            raw=content if error is None else None,
            reasoning=reasoning,
            latency_ms=latency_ms,
            retry_count=attempts,
            error=error,
            model=self.model,
            usage=usage,
        )
