"""Tests for Hy3Provider and MockProvider (P1-T01)."""
from __future__ import annotations

import pytest

from src.llm.hy3_provider import Hy3Provider
from src.llm.mock_provider import MockProvider


def test_mock_provider_returns_deterministic():
    p = MockProvider(default="hello")
    r1 = p.complete([{"role": "user", "content": "x"}])
    r2 = p.complete([{"role": "user", "content": "x"}])
    assert r1.raw == "hello"
    assert r2.raw == "hello"
    assert r1.ok and r2.ok
    assert p.call_count == 2


def test_mock_provider_sequence():
    p = MockProvider(["a", "b"], default="c")
    assert p.complete([]).raw == "a"
    assert p.complete([]).raw == "b"
    assert p.complete([]).raw == "c"
    assert p.complete([]).raw == "c"


def test_hy3_provider_requires_api_key():
    with pytest.raises(ValueError):
        Hy3Provider(api_key="")


class _FakeUsage:
    prompt_tokens = 10
    completion_tokens = 5
    total_tokens = 15


class _FakeMsg:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMsg(content)


class _FakeResp:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]
        self.usage = _FakeUsage()


class _FlakyCompletions:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("flaky transport error")
        return _FakeResp("ok-response")


class _FlakyClient:
    def __init__(self) -> None:
        self.completions = _FlakyCompletions()
        self.chat = self


def test_hy3_provider_retry_and_metadata(monkeypatch):
    fake = _FlakyClient()
    provider = Hy3Provider(
        api_key="k",
        base_url=None,
        model="hy3-model",
        max_retries=2,
        retry_backoff_base=1.0,
        client=fake,
    )
    monkeypatch.setattr("time.sleep", lambda s: None)  # skip real backoff
    result = provider.complete([{"role": "user", "content": "hi"}])
    assert result.ok
    assert result.raw == "ok-response"
    assert result.retry_count == 1
    assert result.latency_ms is not None and result.latency_ms >= 0.0
    assert fake.completions.calls == 2


class _AlwaysFailCompletions:
    def create(self, **kwargs):
        raise RuntimeError("boom")


class _AlwaysFailClient:
    def __init__(self) -> None:
        self.completions = _AlwaysFailCompletions()
        self.chat = self


def test_hy3_provider_error_propagation(monkeypatch):
    provider = Hy3Provider(
        api_key="k",
        model="m",
        max_retries=1,
        retry_backoff_base=1.0,
        client=_AlwaysFailClient(),
    )
    monkeypatch.setattr("time.sleep", lambda s: None)
    result = provider.complete([{"role": "user", "content": "hi"}])
    assert not result.ok
    assert result.raw is None
    assert "boom" in (result.error or "")
    assert result.retry_count == 1


class _FakeReasoningMsg:
    def __init__(self, content: str, reasoning: str | None) -> None:
        self.content = content
        self.reasoning_content = reasoning


class _FakeReasoningChoice:
    def __init__(self, content: str, reasoning: str | None) -> None:
        self.message = _FakeReasoningMsg(content, reasoning)


class _FakeReasoningResp:
    def __init__(self, content: str, reasoning: str | None) -> None:
        self.choices = [_FakeReasoningChoice(content, reasoning)]
        self.usage = _FakeUsage()


class _EmptyThenAnswerCompletions:
    def __init__(self) -> None:
        self.calls = 0
        self.efforts: list[str | None] = []

    def create(self, **kwargs):
        self.calls += 1
        self.efforts.append((kwargs.get("extra_body") or {}).get("reasoning_effort"))
        if self.calls == 1:
            # Deep-thinking mode: content empty, reasoning long.
            return _FakeReasoningResp("", "long hidden chain of thought")
        return _FakeReasoningResp(
            '{"process_correct": true, "first_error_step": null, "reason": "ok"}', "more"
        )


class _EmptyThenAnswerClient:
    def __init__(self) -> None:
        self.completions = _EmptyThenAnswerCompletions()
        self.chat = self


def test_hy3_provider_empty_content_fallback(monkeypatch):
    fake = _EmptyThenAnswerClient()
    provider = Hy3Provider(
        api_key="k",
        model="m",
        max_retries=0,
        retry_backoff_base=1.0,
        empty_content_fallback_effort="low",
        client=fake,
    )
    monkeypatch.setattr("time.sleep", lambda s: None)
    result = provider.complete(
        [{"role": "user", "content": "hi"}], reasoning_effort="high"
    )
    assert result.ok
    assert '"process_correct": true' in (result.raw or "")
    assert result.retry_count == 1  # first attempt + one fallback attempt
    assert result.usage["empty_content_fallback"] == "low"
    assert fake.completions.calls == 2
    assert fake.completions.efforts == ["high", "low"]


def test_hy3_provider_no_fallback_when_disabled(monkeypatch):
    fake = _EmptyThenAnswerClient()
    provider = Hy3Provider(
        api_key="k",
        model="m",
        max_retries=0,
        retry_backoff_base=1.0,
        client=fake,  # fallback not enabled
    )
    monkeypatch.setattr("time.sleep", lambda s: None)
    result = provider.complete(
        [{"role": "user", "content": "hi"}], reasoning_effort="high"
    )
    assert result.ok  # empty content is still a successful call
    assert result.raw == ""
    assert fake.completions.calls == 1


def test_hy3_provider_passes_generation_config(monkeypatch):
    captured: dict = {}

    class _CaptureCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return _FakeResp("ok")

    class _CaptureClient:
        def __init__(self) -> None:
            self.completions = _CaptureCompletions()
            self.chat = self

    provider = Hy3Provider(api_key="k", model="m", client=_CaptureClient())
    provider.complete(
        [{"role": "user", "content": "hi"}],
        temperature=0.0,
        max_tokens=128,
        reasoning_effort="high",
    )
    assert captured["temperature"] == 0.0
    assert captured["max_tokens"] == 128
    assert captured["extra_body"] == {"reasoning_effort": "high"}


class _QuotaFailCompletions:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        raise RuntimeError(
            "Error code: 402 - {'error': {'code': '401008', 'message': 'quota'}}"
        )


def test_hy3_quota_error_is_not_retried(monkeypatch):
    completions = _QuotaFailCompletions()

    class _Client:
        def __init__(self) -> None:
            self.completions = completions
            self.chat = self

    provider = Hy3Provider(
        api_key="k",
        model="m",
        max_retries=3,
        retry_backoff_base=1.0,
        client=_Client(),
    )
    monkeypatch.setattr("time.sleep", lambda s: None)
    result = provider.complete([{"role": "user", "content": "hi"}])
    assert not result.ok
    assert completions.calls == 1
    assert "401008" in (result.error or "")
