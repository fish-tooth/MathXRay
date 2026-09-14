"""Tests for B0 baseline orchestration and resume (P1-T08)."""
from __future__ import annotations

import json

from src.benchmark.processbench_adapter import CanonicalSample
from src.benchmark.runner import (
    align_predictions,
    recompute_metrics,
    run_baseline,
    run_signature,
    stratified_quota,
    stratified_sample,
)
from src.evaluator.direct_judge import DirectJudge
from src.llm.mock_provider import MockProvider

METHOD = "B0-DirectJudge"
PROMPT = "You are a judge."
_RAW = '{"process_correct": false, "first_error_step": 1, "error_type": "LOGIC_GAP", "reason": "x"}'


def _sample(sid: str, *, correct: bool = False, first_error: int | None = 1) -> CanonicalSample:
    return CanonicalSample(
        sample_id=sid,
        problem=f"p {sid}",
        steps=["s1", "s2"],
        source="gsm8k",
        gold_process_correct=correct,
        gold_first_error_step=None if correct else first_error,
    )


def _judge() -> DirectJudge:
    return DirectJudge(MockProvider(default=_RAW), PROMPT, model="mock")


def _sig(prompt: str = PROMPT) -> str:
    return run_signature(
        method=METHOD, model="mock", system_prompt=prompt, generation_config={}
    )


def test_resume_skips_completed_and_does_not_recount(tmp_path):
    samples = [_sample(f"s{i}") for i in range(3)]
    raw_path = tmp_path / "raw.jsonl"

    judge1 = _judge()
    r1 = run_baseline(
        judge1, samples, method=METHOD, run_id="run1", run_signature=_sig(),
        raw_path=raw_path,
    )
    assert r1.n_new == 3
    assert r1.n_resumed == 0
    assert judge1._provider.call_count == 3

    judge2 = _judge()
    r2 = run_baseline(
        judge2, samples, method=METHOD, run_id="run2", run_signature=_sig(),
        raw_path=raw_path,
    )
    assert r2.n_new == 0
    assert r2.n_resumed == 3
    assert judge2._provider.call_count == 0  # no re-computation


def test_resume_reruns_failed_records(tmp_path):
    samples = [_sample("s0")]
    raw_path = tmp_path / "raw.jsonl"

    # First run: provider returns an empty response -> parse failure.
    bad = DirectJudge(MockProvider(default=""), PROMPT, model="mock")
    r1 = run_baseline(
        bad, samples, method=METHOD, run_id="run1", run_signature=_sig(), raw_path=raw_path
    )
    assert r1.n_new == 1
    assert r1.records[0]["prediction"]["parse_status"] == "FAILURE"

    # Second run: good provider. The failed record must NOT be treated as
    # completed, so it is re-judged instead of skipped.
    good = _judge()
    r2 = run_baseline(
        good, samples, method=METHOD, run_id="run2", run_signature=_sig(), raw_path=raw_path
    )
    assert r2.n_resumed == 0
    assert r2.n_new == 1
    assert r2.records[0]["prediction"]["parse_status"] == "SUCCESS"
    assert good._provider.call_count == 1


def test_signature_change_forces_recompute(tmp_path):
    samples = [_sample("s0")]
    raw_path = tmp_path / "raw.jsonl"

    run_baseline(
        _judge(), samples, method=METHOD, run_id="run1", run_signature=_sig("prompt-v1"),
        raw_path=raw_path,
    )
    judge2 = _judge()
    r2 = run_baseline(
        judge2, samples, method=METHOD, run_id="run2", run_signature=_sig("prompt-v2"),
        raw_path=raw_path,
    )
    assert r2.n_new == 1
    assert r2.n_resumed == 0
    assert judge2._provider.call_count == 1


def test_raw_count_matches_samples(tmp_path):
    samples = [_sample(f"s{i}") for i in range(5)]
    raw_path = tmp_path / "raw.jsonl"
    r = run_baseline(
        _judge(), samples, method=METHOD, run_id="run1", run_signature=_sig(),
        raw_path=raw_path,
    )
    lines = [ln for ln in raw_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 5
    assert len(r.records) == 5


def test_raw_record_carries_reasoning(tmp_path):
    samples = [_sample("a")]
    raw_path = tmp_path / "raw.jsonl"
    judge = DirectJudge(MockProvider([_RAW], reasoning="hidden"), PROMPT, model="mock")
    run_baseline(
        judge, samples, method=METHOD, run_id="run1", run_signature=_sig(), raw_path=raw_path
    )
    rec = json.loads(raw_path.read_text(encoding="utf-8"))
    assert rec["prediction"]["reasoning"] == "hidden"


def test_recompute_metrics_from_raw(tmp_path):
    samples = [
        _sample("a", correct=True),
        _sample("b", correct=False, first_error=1),
        _sample("c", correct=False, first_error=2),
    ]
    raw_path = tmp_path / "raw.jsonl"
    r = run_baseline(
        _judge(), samples, method=METHOD, run_id="run1", run_signature=_sig(),
        raw_path=raw_path,
    )
    m = recompute_metrics(r.records, samples)
    assert m.n_all == 3
    assert m.n_gold_correct == 1
    assert m.n_gold_error == 2
    # All predictions locate step 1; only sample b (gold step 1) is exact.
    assert m.first_error_exact == 1 / 2


def test_align_predictions_missing_sample_is_none(tmp_path):
    samples = [_sample("a"), _sample("b")]
    raw_path = tmp_path / "raw.jsonl"
    r = run_baseline(
        _judge(), samples, method=METHOD, run_id="run1", run_signature=_sig(),
        raw_path=raw_path,
    )
    # Drop one record to simulate an incomplete run.
    preds = align_predictions([r.records[0]], samples)
    assert preds[0] is not None
    assert preds[1] is None


def test_stratified_quota_sums_to_n():
    counts = {"gsm8k": 400, "math": 1000, "olympiadbench": 1000, "omnimath": 1000}
    for n in (1, 4, 20, 60, 300):
        quotas = stratified_quota(counts, n)
        assert sum(quotas.values()) == n
        assert set(quotas) == set(counts)


def test_stratified_quota_covers_all_when_room():
    counts = {"gsm8k": 400, "math": 1000, "olympiadbench": 1000, "omnimath": 1000}
    for n in (4, 20, 60, 300):
        quotas = stratified_quota(counts, n)
        assert all(q >= 1 for q in quotas.values())


def test_stratified_quota_small_n():
    counts = {"a": 10, "b": 10, "c": 10}
    assert stratified_quota(counts, 1) == {"a": 1, "b": 0, "c": 0}
    assert stratified_quota(counts, 2) == {"a": 1, "b": 1, "c": 0}


def test_stratified_sample_returns_expected_total():
    rows_by_split = {
        "gsm8k": [f"g{i}" for i in range(400)],
        "math": [f"m{i}" for i in range(1000)],
        "olympiadbench": [f"o{i}" for i in range(1000)],
        "omnimath": [f"n{i}" for i in range(1000)],
    }
    selected = stratified_sample(rows_by_split, 20, seed=42)
    assert len(selected) == 20
    sources = {s for s, _ in selected}
    assert sources == set(rows_by_split)  # every split covered
