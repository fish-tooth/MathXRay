"""Freeze a ProcessBench-style eval slice from the private high-school corpus."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from src.benchmark.highschool import (
    build_eval_samples,
    corpus_stats,
    dump_eval_jsonl,
    load_raw,
    parse_item,
)

STAGE_QUOTAS = {
    "smoke": {"n_wrong": 6, "n_right": 6, "n_official": 6, "n_adversarial": 6},
    "pilot": {"n_wrong": 28, "n_right": 28, "n_official": 16, "n_adversarial": 16},
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default="data/high_school_all_annotated_final.json")
    parser.add_argument("--stage", choices=list(STAGE_QUOTAS), default="pilot")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", default="data/processed")
    args = parser.parse_args(argv)

    rows = load_raw(args.src)
    items = [it for it in (parse_item(row) for row in rows) if it is not None]
    stats = corpus_stats(items)
    quotas = STAGE_QUOTAS[args.stage]
    samples = build_eval_samples(items, seed=args.seed, **quotas)

    out_dir = Path(args.out_dir)
    eval_path = dump_eval_jsonl(out_dir / f"highschool_{args.stage}.jsonl", samples)
    tracks = Counter((s.metadata or {}).get("track") or s.source for s in samples)
    manifest = {
        "stage": args.stage,
        "seed": args.seed,
        "src": args.src,
        "quotas": quotas,
        "n_eval": len(samples),
        "tracks": dict(tracks),
        "sample_ids": [s.sample_id for s in samples],
        "corpus": stats,
        "gold_notes": {
            "qwen_wrong": "answer mismatch ⇒ process invalid; first-error unknown (no M2)",
            "qwen_right": "unlabeled process; unsupported-answer candidates only",
            "official": "textbook analysis as weak gold-correct (M3)",
            "adversarial": "deterministic mutation of official traces (M1/M2)",
        },
    }
    man_path = out_dir / f"highschool_{args.stage}.manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    stats_path = out_dir / "highschool_corpus_stats.json"
    stats_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"corpus n_with_steps={stats['n_with_steps']}")
    print(
        "answer correct/wrong/unknown="
        f"{stats['n_answer_correct']}/{stats['n_answer_wrong']}/{stats['n_answer_unknown']}"
    )
    print(f"eval n={len(samples)} tracks={dict(tracks)}")
    print(f"wrote {eval_path}")
    print(f"wrote {man_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
