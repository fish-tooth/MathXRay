"""Aggregate raw JSONL into official tables, error distributions, and difficulty curves."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.analysis.bootstrap import bootstrap_ci, fmt_ci
from src.analysis.metrics import compute_metrics, group_by_source
from src.benchmark.processbench_adapter import CanonicalSample
from src.benchmark.runner import prediction_from_record
from src.evaluator.direct_judge import JudgePrediction
from src.taxonomy import ERROR_TYPE_LABELS, normalize_error_type

SOURCE_DIFFICULTY = {
    "gsm8k": "D1",
    "math": "D3",
    "olympiadbench": "D4",
    "omnimath": "D5",
}


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def latest_by_sample(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the last record per sample_id (resume may append retries)."""
    by_id: dict[str, dict[str, Any]] = {}
    for rec in records:
        sid = rec.get("sample_id")
        if sid:
            by_id[sid] = rec
    return list(by_id.values())


def samples_from_records(records: list[dict[str, Any]]) -> list[CanonicalSample]:
    samples: list[CanonicalSample] = []
    for rec in records:
        samples.append(
            CanonicalSample(
                sample_id=rec["sample_id"],
                problem="",
                steps=[],
                source=str(rec.get("source") or "unknown"),
                gold_process_correct=bool(rec.get("gold_process_correct")),
                gold_first_error_step=rec.get("gold_first_error_step"),
                gold_final_answer_correct=rec.get("gold_final_answer_correct"),
            )
        )
    return samples


def predictions_from_records(records: list[dict[str, Any]]) -> list[JudgePrediction]:
    return [prediction_from_record(rec) for rec in records]


def error_type_distribution(preds: list[JudgePrediction]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for p in preds:
        if p.process_correct is False:
            counts[normalize_error_type(p.error_type) or "UNKNOWN"] += 1
    return dict(counts)


def unsupported_gold_stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Gold A/P two-way table + evaluator recall on unsupported answers."""
    n_ac = n_ai = n_wc = n_wi = 0
    n_gold_unsup = 0
    n_pred_unsup_hit = 0
    flagged_on_ac = 0
    for rec in records:
        a = rec.get("gold_final_answer_correct")
        p = rec.get("gold_process_correct")
        pred = rec.get("prediction") or {}
        pred_issue = pred.get("process_correct") is False
        if a is True and p is True:
            n_ac += 1
            if pred_issue:
                flagged_on_ac += 1
        elif a is True and p is False:
            n_ai += 1
            n_gold_unsup += 1
            if pred_issue:
                n_pred_unsup_hit += 1
        elif a is False and p is True:
            n_wc += 1
        else:
            n_wi += 1
    return {
        "n_supported_correct": n_ac,
        "n_unsupported_answer": n_ai,
        "n_finalization_fail": n_wc,
        "n_ordinary_fail": n_wi,
        "unsupported_recall": (n_pred_unsup_hit / n_gold_unsup) if n_gold_unsup else None,
        "flag_rate_on_supported_correct": (flagged_on_ac / n_ac) if n_ac else None,
        "n_flagged_on_supported_correct": flagged_on_ac,
    }


def localization_successes(
    records: list[dict[str, Any]],
) -> tuple[list[int], list[int], list[int]]:
    det, exact, correct = [], [], []
    for rec in records:
        gold_ok = bool(rec.get("gold_process_correct"))
        pred = rec.get("prediction") or {}
        pred_ok = pred.get("process_correct")
        if gold_ok:
            correct.append(1 if pred_ok is True else 0)
            continue
        det.append(1 if pred_ok is False else 0)
        gold_step = rec.get("gold_first_error_step")
        pred_step = pred.get("first_error_step")
        exact.append(1 if pred_step is not None and pred_step == gold_step else 0)
    return det, exact, correct


def difficulty_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        src = str(rec.get("source") or "unknown")
        grouped[src].append(rec)
    rows = []
    for src, recs in sorted(grouped.items()):
        samples = samples_from_records(recs)
        preds = predictions_from_records(recs)
        m = compute_metrics(preds, samples)
        rows.append(
            {
                "source": src,
                "difficulty": SOURCE_DIFFICULTY.get(src, "DX"),
                "metrics": m.to_dict(),
            }
        )
    return rows


def capability_boundary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Largest adjacent drop in First-Error Exact ordered by difficulty D1→D5."""
    order = {"D1": 1, "D2": 2, "D3": 3, "D4": 4, "D5": 5}
    seq = [r for r in rows if r.get("difficulty") in order]
    seq.sort(key=lambda r: order[r["difficulty"]])
    best = None
    for a, b in zip(seq, seq[1:]):
        va = a["metrics"].get("first_error_exact")
        vb = b["metrics"].get("first_error_exact")
        if va is None or vb is None:
            continue
        drop = va - vb
        if best is None or drop > best["drop"]:
            best = {
                "from": a["source"],
                "to": b["source"],
                "from_difficulty": a["difficulty"],
                "to_difficulty": b["difficulty"],
                "from_value": va,
                "to_value": vb,
                "drop": drop,
            }
    return best or {}


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    records = latest_by_sample(records)
    samples = samples_from_records(records)
    preds = predictions_from_records(records)
    overall = compute_metrics(preds, samples)
    per_source = {s: m.to_dict() for s, m in group_by_source(preds, samples).items()}
    det, exact, correct = localization_successes(records)
    m1 = bootstrap_ci(det)
    m2 = bootstrap_ci(exact)
    m3 = bootstrap_ci(correct)
    diff_rows = difficulty_rows(records)
    return {
        "n": len(records),
        "metrics": overall.to_dict(),
        "per_source": per_source,
        "ci": {
            "error_detection_recall": {"point": m1[0], "low": m1[1], "high": m1[2], "fmt": fmt_ci(*m1)},
            "first_error_exact": {"point": m2[0], "low": m2[1], "high": m2[2], "fmt": fmt_ci(*m2)},
            "correct_process_accuracy": {
                "point": m3[0],
                "low": m3[1],
                "high": m3[2],
                "fmt": fmt_ci(*m3),
            },
        },
        "error_type_distribution": error_type_distribution(preds),
        "unsupported": unsupported_gold_stats(records),
        "difficulty": diff_rows,
        "capability_boundary": capability_boundary(diff_rows),
        "error_type_labels": ERROR_TYPE_LABELS,
    }


def metrics_markdown(summary: dict[str, Any], title: str) -> str:
    m = summary["metrics"]
    ci = summary.get("ci") or {}

    def fmt(v: Any) -> str:
        if v is None:
            return "-"
        if isinstance(v, float):
            return f"{v:.4f}"
        return str(v)

    lines = [f"# {title}\n", "| Metric | Value | 95% CI |", "|---|---|---|"]
    mapping = [
        ("error_detection_recall", "M1 Error Detection Recall"),
        ("first_error_exact", "M2 First-Error Exact"),
        ("correct_process_accuracy", "M3 Correct Process Accuracy"),
        ("process_status_accuracy", "M4 Process Status Accuracy"),
        ("official_composite", "M5 Official Composite"),
        ("plus_minus_one", "+/-1 Localization"),
    ]
    for key, label in mapping:
        ci_s = (ci.get(key) or {}).get("fmt") or "-"
        lines.append(f"| {label} | {fmt(m.get(key))} | {ci_s} |")
    lines.append("")
    lines.append("| Accounting | Value |")
    lines.append("|---|---|")
    for key in (
        "n_all",
        "n_gold_error",
        "n_gold_correct",
        "n_parse_failure",
        "n_api_failure",
        "n_pred_missing",
        "n_missed_localization",
    ):
        lines.append(f"| {key} | {fmt(m.get(key))} |")

    per = summary.get("per_source") or {}
    if per:
        lines.append("\n## Per-source\n")
        lines.append("| Source | Difficulty | M1 | M2 Exact | M3 Correct | M5 | n |")
        lines.append("|---|---|---|---|---|---|---|")
        for src, row in sorted(per.items()):
            diff = SOURCE_DIFFICULTY.get(src, "DX")
            lines.append(
                f"| {src} | {diff} | {fmt(row.get('error_detection_recall'))} | "
                f"{fmt(row.get('first_error_exact'))} | "
                f"{fmt(row.get('correct_process_accuracy'))} | "
                f"{fmt(row.get('official_composite'))} | {fmt(row.get('n_all'))} |"
            )

    dist = summary.get("error_type_distribution") or {}
    if dist:
        labels = summary.get("error_type_labels") or {}
        lines.append("\n## Predicted error-type distribution (no type gold)\n")
        lines.append("| Type | Label | Count |")
        lines.append("|---|---|---|")
        for k, v in sorted(dist.items(), key=lambda kv: -kv[1]):
            lines.append(f"| {k} | {labels.get(k, k)} | {v} |")

    uns = summary.get("unsupported") or {}
    if uns:
        lines.append("\n## Answer / process two-way (gold)\n")
        lines.append("| Cell | n |")
        lines.append("|---|---|")
        lines.append(f"| Supported correct (A✓ P✓) | {uns.get('n_supported_correct')} |")
        lines.append(f"| Unsupported answer (A✓ P✗) | {uns.get('n_unsupported_answer')} |")
        lines.append(f"| Finalization fail (A✗ P✓) | {uns.get('n_finalization_fail')} |")
        lines.append(f"| Ordinary fail (A✗ P✗) | {uns.get('n_ordinary_fail')} |")
        lines.append(f"| Unsupported recall | {fmt(uns.get('unsupported_recall'))} |")

    bound = summary.get("capability_boundary") or {}
    if bound:
        lines.append("\n## Capability boundary\n")
        lines.append(
            f"Largest adjacent First-Error Exact drop: "
            f"{bound.get('from_difficulty')} ({bound.get('from')}, "
            f"{fmt(bound.get('from_value'))}) → "
            f"{bound.get('to_difficulty')} ({bound.get('to')}, "
            f"{fmt(bound.get('to_value'))}), drop = {fmt(bound.get('drop'))}."
        )
    return "\n".join(lines)


def write_summary(path: str | Path, summary: dict[str, Any], markdown: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    path.with_suffix(".md").write_text(markdown, encoding="utf-8")
