"""B0 baseline run orchestration with resume (P1-T08).

The runner owns the raw-first data flow:

    raw JSONL (append-only, self-contained) -> parsed predictions -> summary metrics

It is deliberately provider-agnostic: it takes a :class:`DirectJudge` (which
wraps any provider), a list of canonical samples, and a raw output path. Resume
is keyed by ``sample_id + method + run_signature`` so that re-running with an
unchanged prompt/config/model skips already-completed samples instead of burning
API quota or double-counting.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.analysis.metrics import MetricsResult, compute_metrics
from src.benchmark.processbench_adapter import CanonicalSample
from src.evaluator.direct_judge import DirectJudge, JudgePrediction
from src.run_metadata import stable_hash


def run_signature(
    *,
    method: str,
    model: str,
    system_prompt: str,
    generation_config: dict[str, Any],
) -> str:
    """Deterministic signature of everything that affects a judge's output.

    Changing the prompt, model, or any generation setting produces a different
    signature, which prevents stale cached predictions from being reused.
    """
    return stable_hash(
        {
            "method": method,
            "model": model,
            "system_prompt": system_prompt,
            "generation_config": generation_config,
        }
    )


def build_raw_record(
    sample: CanonicalSample,
    prediction: JudgePrediction,
    *,
    method: str,
    run_id: str,
    run_signature: str,
) -> dict[str, Any]:
    """Build a self-contained raw JSONL record (gold + prediction + provenance).

    The record carries enough gold information to recompute every metric from the
    raw file alone, which satisfies the raw-first reproducibility requirement.
    """
    return {
        "sample_id": sample.sample_id,
        "method": method,
        "run_id": run_id,
        "run_signature": run_signature,
        "source": sample.source,
        "gold_process_correct": sample.gold_process_correct,
        "gold_first_error_step": sample.gold_first_error_step,
        "gold_final_answer_correct": sample.gold_final_answer_correct,
        "prediction": prediction.to_dict(),
    }


def prediction_from_record(record: dict[str, Any]) -> JudgePrediction:
    """Reconstruct a :class:`JudgePrediction` from a raw record."""
    return JudgePrediction(**record["prediction"])


@dataclass
class RunResult:
    """Outcome of a baseline run: all records plus resume accounting."""

    records: list[dict[str, Any]] = field(default_factory=list)
    n_new: int = 0
    n_resumed: int = 0


def run_baseline(
    judge: DirectJudge,
    samples: list[CanonicalSample],
    *,
    method: str,
    run_id: str,
    run_signature: str,
    raw_path: str | Path,
    resume: bool = True,
    generation_config: dict[str, Any] | None = None,
) -> RunResult:
    """Run the judge over samples, appending raw records and skipping resumed ones.

    ``resume=True`` (default) reads any existing raw file and skips samples whose
    ``(sample_id, method, run_signature)`` already has a *successful* prediction.
    Failed/empty records (parse or API failures) are not counted as completed, so
    re-running retries them instead of burning nothing. New predictions are
    appended to the raw file immediately so an interrupted run can be resumed.
    """
    raw_path = Path(raw_path)
    gen_cfg = generation_config or {}

    completed: set[str] = set()
    existing: list[dict[str, Any]] = []
    if resume and raw_path.exists():
        with raw_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("method") != method or rec.get("run_signature") != run_signature:
                    continue
                pred = rec.get("prediction") or {}
                if pred.get("parse_status") == "SUCCESS" and pred.get("error") is None:
                    completed.add(rec["sample_id"])
                    existing.append(rec)

    new_records: list[dict[str, Any]] = []
    n_resumed = 0
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    with raw_path.open("a", encoding="utf-8") as f:
        for sample in samples:
            if sample.sample_id in completed:
                n_resumed += 1
                continue
            prediction = judge.judge(sample, **gen_cfg)
            record = build_raw_record(
                sample,
                prediction,
                method=method,
                run_id=run_id,
                run_signature=run_signature,
            )
            new_records.append(record)
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return RunResult(records=existing + new_records, n_new=len(new_records), n_resumed=n_resumed)


def align_predictions(
    records: list[dict[str, Any]],
    samples: list[CanonicalSample],
) -> list[JudgePrediction | None]:
    """Align raw records to ``samples`` order, yielding ``None`` for missing ones.

    Samples without a matching record yield ``None`` predictions, which the metric
    layer counts as missing (never silently dropped).
    """
    rec_by_id = {rec["sample_id"]: rec for rec in records}
    return [
        prediction_from_record(rec_by_id[sample.sample_id])
        if sample.sample_id in rec_by_id
        else None
        for sample in samples
    ]


def recompute_metrics(
    records: list[dict[str, Any]],
    samples: list[CanonicalSample],
) -> MetricsResult:
    """Recompute metrics from raw records aligned to ``samples`` order."""
    return compute_metrics(align_predictions(records, samples), list(samples))


def stratified_quota(split_counts: dict[str, int], n: int) -> dict[str, int]:
    """Allocate ``n`` samples across splits proportionally.

    Uses the largest-remainder method so the total exactly equals ``n``. When
    ``n`` is large enough every split gets at least one slot; when ``n`` is
    smaller than the number of splits, the first ``n`` splits get one slot each
    (the caller clamps against the number of available rows).
    """
    names = list(split_counts)
    k = len(names)
    if not names:
        return {}
    if n <= 0:
        return {name: 0 for name in names}

    if n <= k:
        return {name: (1 if i < n else 0) for i, name in enumerate(names)}

    # Every split starts with one slot.
    quotas = {name: 1 for name in names}
    remaining = n - k
    total = sum(split_counts.values())
    weights = [split_counts[name] for name in names]
    raw = [remaining * w / total for w in weights]
    floors = {name: int(raw[i]) for i, name in enumerate(names)}
    for name, f in floors.items():
        quotas[name] += f

    leftover = remaining - sum(floors.values())
    order = sorted(
        names,
        key=lambda nm: -(raw[names.index(nm)] - floors[nm]),
    )
    for name in order[:leftover]:
        quotas[name] += 1
    return quotas


def stratified_sample(
    rows_by_split: dict[str, list[Any]],
    n: int,
    *,
    seed: int,
) -> list[tuple[str, Any]]:
    """Return ``(source, row)`` pairs sampled proportionally across splits."""
    rng = random.Random(seed)
    split_counts = {k: len(v) for k, v in rows_by_split.items()}
    quotas = stratified_quota(split_counts, n)

    selected: list[tuple[str, Any]] = []
    for split, rows in rows_by_split.items():
        quota = min(quotas.get(split, 0), len(rows))
        for row in rng.sample(rows, quota):
            selected.append((split, row))
    return selected
