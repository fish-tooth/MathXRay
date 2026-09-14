"""Prepare a frozen SolveBench subset from GSM8K / MATH / Omni-MATH (R5).

Usage:
    python scripts/prepare_solvebench.py --n 90
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.benchmark.solvebench import (
    DATASET_VERSION,
    dump_jsonl,
    from_gsm8k,
    from_math,
    from_omnimath,
    stratified_by_difficulty,
)
from src.run_metadata import stable_hash


def _try_load(name: str, *args, **kwargs):
    from datasets import load_dataset

    try:
        return load_dataset(name, *args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] failed to load {name}: {exc}")
        return None


def _rows(ds, split_pref: tuple[str, ...]) -> tuple[str, list]:
    if ds is None:
        return "", []
    if hasattr(ds, "keys"):
        for name in split_pref:
            if name in ds:
                return name, list(ds[name])
        name = next(iter(ds.keys()))
        return name, list(ds[name])
    return "default", list(ds)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=90, help="Total frozen sample count.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="data/processed/solvebench.jsonl")
    args = parser.parse_args(argv)

    samples = []

    gsm = _try_load("openai/gsm8k", "main") or _try_load("gsm8k", "main")
    split, rows = _rows(gsm, ("test", "train"))
    samples.extend(from_gsm8k(row, i, split or "test") for i, row in enumerate(rows))

    math_ds = (
        _try_load("hendrycks/competition_math")
        or _try_load("nlile/hendrycks-MATH-benchmark")
        or _try_load("EleutherAI/hendrycks_math", "algebra")
    )
    split, rows = _rows(math_ds, ("test", "train"))
    samples.extend(from_math(row, i, split or "test") for i, row in enumerate(rows))

    omni = (
        _try_load("KbsdJames/Omni-MATH")
        or _try_load("nlile/omni-math")
        or _try_load("Omni-MATH/Omni-MATH")
    )
    split, rows = _rows(omni, ("test", "Train", "train"))
    samples.extend(from_omnimath(row, i, split or "test") for i, row in enumerate(rows) if row)

    usable = [s for s in samples if s.problem.strip() and s.gold_answer.strip()]
    print(f"[prepare] loaded {len(usable)} usable rows "
          f"(gsm8k={sum(1 for s in usable if s.source=='gsm8k')}, "
          f"math={sum(1 for s in usable if s.source=='math')}, "
          f"omnimath={sum(1 for s in usable if s.source=='omnimath')})")

    if not usable:
        print("[prepare] no public datasets available; write empty placeholder")
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text("", encoding="utf-8")
        return 1

    chosen = stratified_by_difficulty(usable, args.n, seed=args.seed)
    path = dump_jsonl(args.out, chosen)
    manifest = {
        "dataset_version": DATASET_VERSION,
        "n": len(chosen),
        "seed": args.seed,
        "ids": [s.sample_id for s in chosen],
        "by_source": {
            src: sum(1 for s in chosen if s.source == src)
            for src in ("gsm8k", "math", "omnimath")
        },
        "by_difficulty": {
            d: sum(1 for s in chosen if s.difficulty == d)
            for d in ("D1", "D2", "D3", "D4", "D5")
        },
        "manifest_hash": stable_hash([s.sample_id for s in chosen]),
    }
    man_path = Path(args.out).with_suffix(".manifest.json")
    man_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[prepare] wrote {path} n={len(chosen)}")
    print(f"[prepare] manifest {man_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
