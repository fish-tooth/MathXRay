"""B0 — Hy3 Direct Judge baseline (EXT-01 / P1-T06).

Feeds the problem + the explicit reasoning steps to Hy3 in a single pass and asks
it to predict ``process_correct`` and the first error step directly. This is the
mandatory baseline that any full hybrid evaluator must be compared against on the
same benchmark / model / generation settings.

The judge is a thin, provider-agnostic wrapper: it builds messages, calls the
provider, and parses the structured JSON response into a :class:`JudgePrediction`.
Parse failures are recorded explicitly and never silently dropped (protocol P-05).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from src.benchmark.processbench_adapter import CanonicalSample
from src.llm.base import BaseLLMProvider

# First-level error taxonomy shared with the protocol (R2.3 / R8).
ERROR_TYPES = {
    "PROBLEM_MISREAD",
    "CONDITION_OMISSION",
    "CONCEPT_ERROR",
    "THEOREM_MISUSE",
    "LOGIC_GAP",
    "CIRCULAR_REASONING",
    "ALGEBRA_ERROR",
    "ARITHMETIC_ERROR",
    "HALLUCINATION",
    "ANSWER_FORMAT_ERROR",
    "OTHER",
}


@dataclass
class JudgePrediction:
    """A single Direct-Judge prediction with provenance metadata."""

    sample_id: str
    process_correct: bool | None = None
    first_error_step: int | None = None  # 1-based; None means "no error" or "not located"
    error_type: str | None = None
    reason: str = ""
    raw: str = ""
    reasoning: str = ""  # provider's hidden chain-of-thought, if exposed
    parse_status: str = "PENDING"  # SUCCESS | FAILURE
    parse_error: str | None = None
    error: str | None = None  # API/transport failure
    latency_ms: float | None = None
    retry_count: int = 0
    model: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ParseJudgeResult:
    status: str  # SUCCESS | FAILURE
    process_correct: bool | None = None
    first_error_step: int | None = None
    error_type: str | None = None
    reason: str = ""
    error: str | None = None


def _extract_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError("no valid JSON object found in response")


def extract_json_object(text: str) -> Any:
    """Best-effort JSON object extraction from a model response."""
    return _extract_json(text)


def parse_judge_raw(raw: str) -> ParseJudgeResult:
    if not raw or not raw.strip():
        return ParseJudgeResult(status="FAILURE", error="empty response")

    try:
        data = _extract_json(raw)
    except ValueError as exc:
        return ParseJudgeResult(status="FAILURE", error=f"JSON decode failed: {exc}")

    if not isinstance(data, dict):
        return ParseJudgeResult(status="FAILURE", error="top-level JSON must be an object")

    pc = data.get("process_correct")
    if not isinstance(pc, bool):
        return ParseJudgeResult(
            status="FAILURE", error="'process_correct' must be a boolean"
        )

    fes = data.get("first_error_step")
    if isinstance(fes, bool):
        return ParseJudgeResult(
            status="FAILURE", error="'first_error_step' must be an integer or null"
        )
    if fes is not None and (not isinstance(fes, int) or fes < 1):
        return ParseJudgeResult(
            status="FAILURE", error="'first_error_step' must be a positive integer or null"
        )

    # Consistency guard: a correct process cannot carry a located error.
    if pc is True and fes is not None:
        return ParseJudgeResult(
            status="FAILURE",
            error="'first_error_step' must be null when 'process_correct' is true",
        )

    error_type = data.get("error_type")
    if error_type is not None and not isinstance(error_type, str):
        return ParseJudgeResult(
            status="FAILURE", error="'error_type' must be a string or null"
        )

    return ParseJudgeResult(
        status="SUCCESS",
        process_correct=pc,
        first_error_step=fes,
        error_type=error_type,
        reason=str(data.get("reason") or ""),
    )


def build_judge_messages(sample: CanonicalSample, system_prompt: str) -> list[dict[str, str]]:
    """Build the (system, user) messages for a Direct-Judge call."""
    steps_text = "\n".join(
        f"Step {i}: {step}" for i, step in enumerate(sample.steps, start=1)
    )
    user = f"Problem:\n{sample.problem}\n\nReasoning steps:\n{steps_text}"
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user},
    ]


class DirectJudge:
    """B0 Direct Hy3 Judge: one provider call per sample, structured output."""

    name = "B0-DirectJudge"

    def __init__(self, provider: BaseLLMProvider, system_prompt: str, *, model: str = "") -> None:
        self._provider = provider
        self._system_prompt = system_prompt
        self._model = model

    def judge(self, sample: CanonicalSample, **gen_cfg: Any) -> JudgePrediction:
        messages = build_judge_messages(sample, self._system_prompt)
        result = self._provider.complete(messages, **gen_cfg)

        if not result.ok:
            return JudgePrediction(
                sample_id=sample.sample_id,
                raw=result.raw or "",
                reasoning=result.reasoning or "",
                parse_status="FAILURE",
                parse_error=result.error,
                error=result.error,
                latency_ms=result.latency_ms,
                retry_count=result.retry_count,
                model=result.model,
            )

        parsed = parse_judge_raw(result.raw or "")
        return JudgePrediction(
            sample_id=sample.sample_id,
            process_correct=parsed.process_correct,
            first_error_step=parsed.first_error_step,
            error_type=parsed.error_type,
            reason=parsed.reason,
            raw=result.raw or "",
            reasoning=result.reasoning or "",
            parse_status=parsed.status,
            parse_error=parsed.error,
            error=result.error,
            latency_ms=result.latency_ms,
            retry_count=result.retry_count,
            model=result.model,
        )
