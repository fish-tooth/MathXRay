"""Tests for hybrid fusion (symbolic priority, no extra API)."""

from __future__ import annotations

from src.evaluator.direct_judge import JudgePrediction
from src.evaluator.hybrid import HybridEvaluator, fuse_step
from src.evaluator.symbolic import INVALID, UNKNOWN, VALID


def test_fuse_invalid_wins():
    assert fuse_step(INVALID, VALID) == INVALID
    assert fuse_step(VALID, INVALID) == INVALID
    assert fuse_step(UNKNOWN, UNKNOWN) == UNKNOWN
    assert fuse_step(VALID, VALID) == VALID


def test_symbolic_invalid_overrides_semantic_correct():
    semantic = JudgePrediction(
        sample_id="s",
        process_correct=True,
        first_error_step=None,
        parse_status="SUCCESS",
        reason="looks fine",
    )
    audit = HybridEvaluator().audit_texts(
        ["1+1=2", "2+2=5"],
        sample_id="s",
        semantic=semantic,
    )
    assert audit.process_correct is False
    assert audit.first_error_step == 2
    assert audit.disagreement is True
    assert audit.step_audits[1].dependency_tag == "ROOT"


def test_semantic_error_when_symbolic_unknown():
    semantic = JudgePrediction(
        sample_id="s",
        process_correct=False,
        first_error_step=1,
        error_type="THEOREM_MISUSE",
        parse_status="SUCCESS",
        reason="wrong theorem",
    )
    audit = HybridEvaluator().audit_texts(
        ["apply AM-GM without checking equality case"],
        sample_id="s",
        semantic=semantic,
    )
    assert audit.process_correct is False
    assert audit.first_error_step == 1
    assert audit.error_type == "THEOREM_MISUSE"


def test_both_correct():
    semantic = JudgePrediction(
        sample_id="s",
        process_correct=True,
        parse_status="SUCCESS",
        reason="ok",
    )
    audit = HybridEvaluator().audit_texts(["1+1=2", "2+2=4"], semantic=semantic)
    assert audit.process_correct is True
    assert audit.first_error_step is None
