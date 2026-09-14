"""Build TraceAdversarialBench from gold-correct ProcessBench traces."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from datasets import load_dataset

from src.benchmark.adversarial import build_adversarial, dump_jsonl
from src.benchmark.processbench_adapter import to_canonical
from src.run_metadata import stable_hash


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=80)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="data/processed/adversarial.jsonl")
    args = parser.parse_args(argv)

    ds = load_dataset("Qwen/ProcessBench", "default")
    correct = []
    for split in ds.keys():
        for row in ds[split]:
            sample = to_canonical(row, source=split)
            if sample.gold_process_correct:
                correct.append(sample)
    print(f"[adv] gold-correct traces: {len(correct)}")
    items = build_adversarial(correct, n=args.n, seed=args.seed)
    path = dump_jsonl(args.out, items)
    manifest = {
        "n": len(items),
        "seed": args.seed,
        "mutations": {
            m: sum(1 for x in items if x.mutation == m)
            for m in ("arithmetic", "sign", "operator", "unused_claim")
        },
        "n_answer_preserving": sum(1 for x in items if x.answer_preserving),
        "ids": [x.sample_id for x in items],
        "manifest_hash": stable_hash([x.sample_id for x in items]),
    }
    man = Path(args.out).with_suffix(".manifest.json")
    man.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[adv] wrote {path} n={len(items)} -> {man}")
    return 0 if items else 1


if __name__ == "__main__":
    sys.exit(main())
