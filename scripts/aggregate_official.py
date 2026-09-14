"""Aggregate existing ProcessBench raw files into official tables (no extra API)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.analysis.reporting import (
    latest_by_sample,
    load_jsonl,
    metrics_markdown,
    summarize_records,
    write_summary,
)


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
    parser.add_argument("--out-dir", default="reports/official")
    args = parser.parse_args(argv)

    records: list[dict] = []
    for path in args.raw:
        p = Path(path)
        if not p.exists():
            print(f"[skip] {path}")
            continue
        records.extend(load_jsonl(p))
    records = latest_by_sample(records)
    if not records:
        print("[aggregate] no records")
        return 1

    overall = summarize_records(records)
    overall["sources_used"] = sorted({r.get("source") for r in records})
    overall["raw_files"] = [str(p) for p in args.raw if Path(p).exists()]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_summary(
        out_dir / "processbench_overall.json",
        overall,
        metrics_markdown(overall, "ProcessBench B0 Direct-Judge (three-dataset overall)"),
    )

    for source in sorted({r.get("source") for r in records}):
        subset = [r for r in records if r.get("source") == source]
        summary = summarize_records(subset)
        write_summary(
            out_dir / f"processbench_{source}.json",
            summary,
            metrics_markdown(summary, f"ProcessBench / {source}"),
        )

    # Combined three-dataset view requested by the contest: GSM8K + MATH + Omni-MATH.
    three = [r for r in records if r.get("source") in {"gsm8k", "math", "omnimath"}]
    if three:
        summary = summarize_records(three)
        summary["note"] = (
            "Official three-dataset slice: GSM8K (D1), MATH (D3), Omni-MATH (D5). "
            "OlympiadBench is reported separately as an extra high-difficulty split."
        )
        write_summary(
            out_dir / "processbench_three_datasets.json",
            summary,
            metrics_markdown(summary, "Three datasets: GSM8K + MATH + Omni-MATH"),
        )

    index = {
        "n_all": overall["n"],
        "files": [p.name for p in sorted(out_dir.glob("*.json"))],
    }
    (out_dir / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[aggregate] n={overall['n']} -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
