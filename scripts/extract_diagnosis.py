"""Extract a human-checkable diagnosis set from a B0 baseline raw file (P1-T10).

Reads ``results/raw/B0-DirectJudge_<stage>.jsonl`` (latest record per sample_id),
classifies gold-vs-prediction disagreements, and writes a Markdown report.

Categories:
  - MISS: gold process invalid, judge says correct (error detection miss)
  - FALSE_ALARM: gold process correct, judge says error (false positive)
  - LOCALIZE_OFF: both invalid, but located first-error step differs
  - PARSE_FAIL: prediction could not be parsed (raw empty / bad JSON)
  - API_FAIL: transport/provider error recorded on the record
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

from src.analysis.reporting import latest_by_sample, load_jsonl


def _problem_for(cache: dict[str, str], sample_id: str) -> str:
    return cache.get(sample_id, "")


def _load_problems() -> dict[str, str]:
    try:
        from datasets import load_dataset
    except Exception:
        return {}
    cache: dict[str, str] = {}
    try:
        ds = load_dataset("Qwen/ProcessBench", "default")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] ProcessBench not loaded ({exc}); problem text omitted")
        return cache
    for split in ds:
        for row in ds[split]:
            cache[str(row["id"])] = str(row["problem"])
    return cache


def _classify(rec: dict) -> str:
    pred = rec.get("prediction") or {}
    if rec.get("error") or pred.get("error"):
        return "API_FAIL"
    status = str(pred.get("parse_status") or "")
    if status == "FAILURE" or pred.get("process_correct") is None:
        return "PARSE_FAIL"
    gold_ok = bool(rec.get("gold_process_correct"))
    pred_ok = bool(pred.get("process_correct"))
    if gold_ok and not pred_ok:
        return "FALSE_ALARM"
    if (not gold_ok) and pred_ok:
        return "MISS"
    if (not gold_ok) and (not pred_ok):
        if pred.get("first_error_step") != rec.get("gold_first_error_step"):
            return "LOCALIZE_OFF"
    return "AGREE"


def _clip(text: str, n: int = 280) -> str:
    text = (text or "").replace("\n", " ").strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def render(records: list[dict], problems: dict[str, str], sources_note: str) -> str:
    buckets: dict[str, list[dict]] = defaultdict(list)
    per_source: dict[str, Counter] = defaultdict(Counter)
    for rec in records:
        cat = _classify(rec)
        buckets[cat].append(rec)
        per_source[str(rec.get("source") or "?")][cat] += 1

    order = ["AGREE", "MISS", "FALSE_ALARM", "LOCALIZE_OFF", "PARSE_FAIL", "API_FAIL"]
    counts = {k: len(buckets.get(k, [])) for k in order}
    n_review = counts["MISS"] + counts["FALSE_ALARM"] + counts["LOCALIZE_OFF"] + counts["PARSE_FAIL"]

    lines = [
        "# Baseline Diagnosis (human verification checklist)",
        "",
        f"- Source: {sources_note}",
        "  (latest record per sample_id). Agreement/disagreement counts below;",
        "  every non-agree sample is listed for manual review before Gate G1.",
        "",
        "## Summary",
        "| Category | n |",
        "|---|---|",
    ]
    for k in order:
        lines.append(f"| {k} | {counts[k]} |")
    lines.append("")
    lines.append(f"Samples requiring verification (non-AGREE, excluding API_FAIL): **{n_review}**.")
    lines.append("")
    lines.append("## Per-source")
    lines.append("| Source | AGREE | MISS | FALSE_ALARM | LOCALIZE_OFF | PARSE_FAIL | API_FAIL |")
    lines.append("|---|---|---|---|---|---|---|")
    for src in sorted(per_source):
        c = per_source[src]
        lines.append(
            f"| {src} | {c['AGREE']} | {c['MISS']} | {c['FALSE_ALARM']} | "
            f"{c['LOCALIZE_OFF']} | {c['PARSE_FAIL']} | {c['API_FAIL']} |"
        )

    def emit(title: str, key: str, extra: str) -> None:
        rows = buckets.get(key) or []
        lines.append("")
        lines.append(f"## {title} ({len(rows)})")
        if extra:
            lines.append("")
            lines.append(extra)
        if not rows:
            lines.append("")
            lines.append("_none_")
            return
        for rec in rows:
            pred = rec.get("prediction") or {}
            sid = rec.get("sample_id")
            lines.append("")
            lines.append(f"### `{sid}` ({rec.get('source')})")
            lines.append("")
            lines.append(
                f"- gold: process_correct={rec.get('gold_process_correct')} "
                f"first_error={rec.get('gold_first_error_step')} "
                f"A_correct={rec.get('gold_final_answer_correct')}"
            )
            lines.append(
                f"- pred: process_correct={pred.get('process_correct')} "
                f"first_error={pred.get('first_error_step')} "
                f"type={pred.get('error_type')} parse={pred.get('parse_status')}"
            )
            if pred.get("reason"):
                lines.append(f"- reason: {_clip(str(pred.get('reason')))}")
            problem = _problem_for(problems, str(sid))
            if problem:
                lines.append(f"- problem: {_clip(problem)}")

    emit("MISS — gold invalid, judge said correct", "MISS", "Costliest error: missed a real process error.")
    emit("FALSE_ALARM — judge said invalid, gold says correct", "FALSE_ALARM", "")
    emit("LOCALIZE_OFF — both invalid, first-error step differs", "LOCALIZE_OFF", "")
    emit("PARSE_FAIL — prediction unusable", "PARSE_FAIL", "")
    emit("API_FAIL — provider/transport error", "API_FAIL", "")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw",
        nargs="+",
        default=[
            "results/raw/B0-DirectJudge_pilot.jsonl",
            "results/raw/B0-DirectJudge_dev.jsonl",
        ],
    )
    parser.add_argument("--out", default="reports/baseline_diagnosis.md")
    parser.add_argument("--skip-problems", action="store_true")
    args = parser.parse_args(argv)

    records: list[dict] = []
    used = []
    for path in args.raw:
        p = Path(path)
        if not p.exists():
            print(f"[skip] {path}")
            continue
        used.append(str(p))
        records.extend(load_jsonl(p))
    records = latest_by_sample(records)
    if not records:
        print("[extract] no records")
        return 1

    problems = {} if args.skip_problems else _load_problems()
    text = render(records, problems, ", ".join(f"`{u}`" for u in used))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"[extract] n={len(records)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
