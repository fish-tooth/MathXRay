"""ProcessBench-style stepwise critique: per-paragraph VALID/INVALID/UNKNOWN."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from src.evaluator.direct_judge import extract_json_object
from src.taxonomy import normalize_error_type

VERDICTS = {"VALID", "INVALID", "UNKNOWN"}
BOXED_INDEX = re.compile(r"\\boxed\{(-?\d+)\}")


@dataclass
class StepVerdict:
    step_id: int
    verdict: str
    claim: str = ""
    error_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "verdict": self.verdict,
            "claim": self.claim,
            "error_type": self.error_type,
        }


@dataclass
class StepwiseResult:
    status: str  # SUCCESS | FAILURE
    steps: list[StepVerdict] = field(default_factory=list)
    process_correct: bool | None = None
    first_error_step: int | None = None
    error_type: str | None = None
    reason: str = ""
    unknown_steps: list[int] = field(default_factory=list)
    error: str | None = None
    raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "steps": [s.to_dict() for s in self.steps],
            "process_correct": self.process_correct,
            "first_error_step": self.first_error_step,
            "error_type": self.error_type,
            "reason": self.reason,
            "unknown_steps": self.unknown_steps,
            "error": self.error,
        }


def tagged_paragraphs(steps: list[str]) -> str:
    blocks = []
    for i, step in enumerate(steps, start=1):
        blocks.append(f"<paragraph_{i}>\n{step}\n</paragraph_{i}>")
    return "\n\n".join(blocks)


def build_stepwise_messages(problem: str, steps: list[str], system_prompt: str) -> list[dict[str, str]]:
    user = f"Problem:\n{problem}\n\nStudent solution:\n{tagged_paragraphs(steps)}"
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user},
    ]


def _boxed_fallback(raw: str, n_steps: int) -> StepwiseResult | None:
    matches = BOXED_INDEX.findall(raw or "")
    if not matches:
        return None
    try:
        idx = int(matches[-1])
    except ValueError:
        return None
    if idx == -1:
        rows = [StepVerdict(i, "VALID") for i in range(1, n_steps + 1)]
        return StepwiseResult(
            status="SUCCESS",
            steps=rows,
            process_correct=True,
            first_error_step=None,
            reason="boxed -1",
            raw=raw,
        )
    if idx < 0:
        return None
    step_id = idx + 1 if idx == 0 and n_steps >= 1 else idx
    # Accept 0-based ProcessBench indexes when 0 is boxed.
    if idx == 0:
        step_id = 1
    if step_id < 1 or step_id > n_steps:
        return None
    rows = [
        StepVerdict(i, "INVALID" if i == step_id else ("VALID" if i < step_id else "UNKNOWN"))
        for i in range(1, n_steps + 1)
    ]
    return StepwiseResult(
        status="SUCCESS",
        steps=rows,
        process_correct=False,
        first_error_step=step_id,
        reason="boxed index fallback",
        raw=raw,
    )


def derive_verdict(rows: list[StepVerdict], n_steps: int) -> tuple[bool | None, int | None, str | None, list[int]]:
    """Recompute process status from per-step verdicts (do not trust model summary)."""
    by_id = {r.step_id: r for r in rows if 1 <= r.step_id <= n_steps}
    unknown = [
        i
        for i in range(1, n_steps + 1)
        if by_id.get(i) is not None and by_id[i].verdict == "UNKNOWN"
    ]
    for i in range(1, n_steps + 1):
        row = by_id.get(i)
        if row and row.verdict == "INVALID":
            return False, i, row.error_type, unknown
    if unknown:
        return None, None, None, unknown
    return True, None, None, []


def parse_stepwise_raw(raw: str, n_steps: int) -> StepwiseResult:
    if not raw or not raw.strip():
        boxed = _boxed_fallback(raw, n_steps)
        return boxed or StepwiseResult(status="FAILURE", error="empty response", raw=raw or "")
    data: Any = None
    try:
        data = extract_json_object(raw)
    except ValueError:
        boxed = _boxed_fallback(raw, n_steps)
        if boxed:
            return boxed
        return StepwiseResult(status="FAILURE", error="JSON decode failed", raw=raw)
    if not isinstance(data, dict):
        return StepwiseResult(status="FAILURE", error="top-level JSON must be an object", raw=raw)
    items = data.get("steps")
    if not isinstance(items, list) or not items:
        boxed = _boxed_fallback(raw, n_steps)
        return boxed or StepwiseResult(status="FAILURE", error="'steps' must be a non-empty list", raw=raw)
    rows: list[StepVerdict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        sid = item.get("step_id")
        if not isinstance(sid, int) or sid < 1:
            continue
        verdict = str(item.get("verdict") or "").strip().upper()
        if verdict not in VERDICTS:
            continue
        err = item.get("error_type")
        err_s = normalize_error_type(err) if verdict == "INVALID" else None
        rows.append(
            StepVerdict(
                step_id=sid,
                verdict=verdict,
                claim=str(item.get("claim") or ""),
                error_type=err_s,
            )
        )
    if not rows:
        return StepwiseResult(status="FAILURE", error="no valid step verdicts", raw=raw)
    process_correct, first_error, error_type, unknown = derive_verdict(rows, n_steps)
    return StepwiseResult(
        status="SUCCESS",
        steps=rows,
        process_correct=process_correct,
        first_error_step=first_error,
        error_type=error_type,
        reason=str(data.get("reason") or ""),
        unknown_steps=unknown,
        raw=raw,
    )
