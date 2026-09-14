"""Replay B0 predictions through the Full hybrid (symbolic + dependency), no extra API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from datasets import load_dataset

from src.analysis.metrics import compute_metrics
from src.analysis.reporting import latest_by_sample, load_jsonl, metrics_markdown, write_summary
from src.benchmark.processbench_adapter import to_canonical
from src.benchmark.runner import prediction_from_record
from src.evaluator.direct_judge import JudgePrediction
from src.evaluator.hybrid import HybridEvaluator


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", default="results/raw/B0-DirectJudge_dev.jsonl")
    parser.add_argument("--out", default="reports/official/processbench_full_replay.json")
    args = parser.parse_args(argv)

    records = latest_by_sample(load_jsonl(args.raw))
    by_id = {r["sample_id"]: r for r in records}
    needed = set(by_id)
    ds = load_dataset("Qwen/ProcessBench", "default")
    hybrid = HybridEvaluator(judge=None)

    golds = []
    fused = []
    b0 = []
    seen = 0
    for split in ds.keys():
        for row in ds[split]:
            sid = str(row["id"])
            if sid not in needed:
                continue
            sample = to_canonical(row, source=split)
            rec = by_id[sample.sample_id]
            golds.append(sample)
            semantic = prediction_from_record(rec)
            b0.append(semantic)
            print(f"[replay] start {seen+1}/{len(needed)} {split}:{sample.sample_id} steps={len(sample.steps)}", flush=True)
            audit = hybrid.audit_texts(
                sample.steps,
                sample_id=sample.sample_id,
                problem=sample.problem,
                source=sample.source,
                semantic=semantic,
            )
            fused.append(
                JudgePrediction(
                    sample_id=sample.sample_id,
                    process_correct=audit.process_correct,
                    first_error_step=audit.first_error_step,
                    error_type=audit.error_type,
                    parse_status="SUCCESS"
                    if audit.process_correct is not None
                    else "FAILURE",
                )
            )
            seen += 1
            if seen % 25 == 0 or seen == len(needed):
                print(f"[replay] {seen}/{len(needed)} {split}:{sample.sample_id}", flush=True)

    b0_m = compute_metrics(b0, golds)
    full_m = compute_metrics(fused, golds)
    delta = None
    if b0_m.first_error_exact is not None and full_m.first_error_exact is not None:
        delta = full_m.first_error_exact - b0_m.first_error_exact
    payload = {
        "n": len(golds),
        "B0": b0_m.to_dict(),
        "Full": full_m.to_dict(),
        "delta_first_error_exact": delta,
        "note": (
            "Full replay fuses stored B0 semantic predictions with the local "
            "symbolic verifier. No extra Hy3 calls."
        ),
    }
    path = Path(args.out)
    write_summary(path, payload, metrics_markdown({"metrics": full_m.to_dict(), "ci": {}, "per_source": {}, "error_type_distribution": {}, "unsupported": {}, "capability_boundary": {}}, "Full hybrid replay on ProcessBench"))
    # overwrite json with the richer payload
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
