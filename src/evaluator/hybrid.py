"""Hybrid process evaluator: symbolic + Hy3 semantic judge + dependency (EXT-05).

Deterministic INVALID evidence has priority. UNKNOWN never masquerades as VALID.
The semantic judge still owns theorem / condition / logic-gap errors that SymPy
cannot see.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.benchmark.processbench_adapter import CanonicalSample
from src.evaluator.dependency import DependencyGraph, build_graph
from src.evaluator.direct_judge import DirectJudge, JudgePrediction
from src.evaluator.symbolic import (
    INVALID,
    UNKNOWN,
    VALID,
    StepSymbolicResult,
    first_symbolic_invalid,
    verify_step,
)
from src.taxonomy import normalize_error_type


@dataclass
class StepAudit:
    step_id: int
    text: str
    symbolic_verdict: str = UNKNOWN
    semantic_verdict: str = UNKNOWN
    fused_verdict: str = UNKNOWN
    dependency_tag: str = "NONE"
    evidence: str = ""


@dataclass
class ProcessAudit:
    sample_id: str
    process_correct: bool | None
    first_error_step: int | None
    first_root_error: int | None
    error_type: str | None
    reason: str
    confidence: str  # High | Medium | Low
    disagreement: bool
    step_audits: list[StepAudit] = field(default_factory=list)
    graph: DependencyGraph | None = None
    semantic: JudgePrediction | None = None
    symbolic_coverage: float = 0.0
    method: str = "Full"

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "process_correct": self.process_correct,
            "first_error_step": self.first_error_step,
            "first_root_error": self.first_root_error,
            "error_type": self.error_type,
            "reason": self.reason,
            "confidence": self.confidence,
            "disagreement": self.disagreement,
            "symbolic_coverage": self.symbolic_coverage,
            "method": self.method,
            "step_audits": [
                {
                    "step_id": s.step_id,
                    "text": s.text,
                    "symbolic_verdict": s.symbolic_verdict,
                    "semantic_verdict": s.semantic_verdict,
                    "fused_verdict": s.fused_verdict,
                    "dependency_tag": s.dependency_tag,
                    "evidence": s.evidence,
                }
                for s in self.step_audits
            ],
        }


def _confidence(*, disagreement: bool, symbolic_invalid: bool, semantic_ok: bool) -> str:
    if disagreement:
        return "Low"
    if symbolic_invalid or semantic_ok:
        return "High"
    return "Medium"


def fuse_step(symbolic: str, semantic: str) -> str:
    """Deterministic INVALID wins; UNKNOWN never upgrades to VALID."""
    if symbolic == INVALID or semantic == INVALID:
        return INVALID
    if symbolic == VALID and semantic == VALID:
        return VALID
    if symbolic == VALID and semantic == UNKNOWN:
        return VALID
    if semantic == VALID and symbolic == UNKNOWN:
        return VALID
    return UNKNOWN


class HybridEvaluator:
    """Full process evaluator used by the application and ablation runs."""

    name = "Full"

    def __init__(self, judge: DirectJudge | None = None) -> None:
        self._judge = judge

    def audit_texts(
        self,
        steps: list[str],
        *,
        sample_id: str = "",
        expressions: list[str | None] | None = None,
        depends_on: dict[int, list[int]] | None = None,
        semantic: JudgePrediction | None = None,
        problem: str = "",
        source: str = "app",
    ) -> ProcessAudit:
        expressions = expressions or [None] * len(steps)
        symbolic_rows: list[StepSymbolicResult] = [
            verify_step(i, text, expressions[i - 1] if i - 1 < len(expressions) else None)
            for i, text in enumerate(steps, start=1)
        ]
        n_decided = sum(1 for r in symbolic_rows if r.verdict != UNKNOWN)
        coverage = n_decided / len(steps) if steps else 0.0
        sym_first = first_symbolic_invalid(symbolic_rows)

        if semantic is None and self._judge is not None:
            sample = CanonicalSample(
                sample_id=sample_id or "adhoc",
                problem=problem or "(user problem)",
                steps=steps,
                source=source,
            )
            semantic = self._judge.judge(sample)

        sem_invalid = bool(semantic and semantic.process_correct is False)
        sem_correct = bool(semantic and semantic.process_correct is True)
        sem_first = semantic.first_error_step if semantic else None

        disagreement = False
        if sym_first is not None and sem_correct:
            disagreement = True
        if sym_first is None and sem_invalid:
            # Possible: semantic caught a non-symbolic error. Not a conflict.
            disagreement = False
        if (
            sym_first is not None
            and sem_invalid
            and sem_first is not None
            and sem_first != sym_first
        ):
            disagreement = True

        if sym_first is not None:
            first_error = sym_first
            process_correct = False
            error_type = normalize_error_type(
                semantic.error_type if semantic and not sem_correct else None
            ) or "ARITHMETIC_ERROR"
            reason = next(
                (r.evidence for r in symbolic_rows if r.step_id == sym_first),
                "symbolic invalid",
            )
            if semantic and semantic.reason and not sem_correct:
                reason = f"{reason}; semantic: {semantic.reason}"
        elif sem_invalid:
            first_error = sem_first
            process_correct = False
            error_type = normalize_error_type(semantic.error_type if semantic else None)
            reason = (semantic.reason if semantic else "") or "semantic judge flagged an error"
        elif sem_correct:
            first_error = None
            process_correct = True
            error_type = None
            reason = (semantic.reason if semantic else "") or "no invalid evidence"
        else:
            # No semantic result (or parse failure) and no symbolic INVALID.
            first_error = None
            process_correct = None if not symbolic_rows else True
            error_type = None
            reason = "no deterministic invalid evidence"
            if semantic and semantic.parse_status == "FAILURE":
                process_correct = None
                reason = semantic.parse_error or semantic.error or "semantic judge failed"

        graph = build_graph(
            len(steps),
            first_error_step=first_error,
            depends_on=depends_on,
        )

        audits: list[StepAudit] = []
        for i, text in enumerate(steps, start=1):
            sym_v = symbolic_rows[i - 1].verdict
            if process_correct is True:
                sem_v = VALID
            elif first_error == i:
                sem_v = INVALID if sem_invalid or sym_first == i else UNKNOWN
            elif first_error is not None and i > first_error:
                sem_v = UNKNOWN
            else:
                sem_v = VALID if process_correct is True else UNKNOWN
            fused = fuse_step(sym_v, sem_v if first_error == i or process_correct else UNKNOWN)
            if first_error == i:
                fused = INVALID
            elif process_correct is True:
                fused = fuse_step(sym_v, VALID)
            audits.append(
                StepAudit(
                    step_id=i,
                    text=text,
                    symbolic_verdict=sym_v,
                    semantic_verdict=sem_v,
                    fused_verdict=fused,
                    dependency_tag=graph.tag_for(i),
                    evidence=symbolic_rows[i - 1].evidence,
                )
            )

        conf = _confidence(
            disagreement=disagreement,
            symbolic_invalid=sym_first is not None,
            semantic_ok=sem_correct or (sem_invalid and not disagreement),
        )
        return ProcessAudit(
            sample_id=sample_id,
            process_correct=process_correct,
            first_error_step=first_error,
            first_root_error=graph.first_root_error,
            error_type=error_type,
            reason=reason,
            confidence=conf,
            disagreement=disagreement,
            step_audits=audits,
            graph=graph,
            semantic=semantic,
            symbolic_coverage=coverage,
        )

    def audit_sample(self, sample: CanonicalSample, **gen_cfg: Any) -> ProcessAudit:
        semantic = None
        if self._judge is not None:
            semantic = self._judge.judge(sample, **gen_cfg)
        return self.audit_texts(
            sample.steps,
            sample_id=sample.sample_id,
            problem=sample.problem,
            source=sample.source,
            semantic=semantic,
        )
