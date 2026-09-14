"""Evaluate DirectJudge / Full hybrid on TraceAdversarialBench."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.analysis.metrics import compute_metrics
from src.benchmark.adversarial import load_jsonl
from src.benchmark.runner import build_raw_record, run_signature
from src.config import load_config
from src.evaluator.direct_judge import JudgePrediction
from src.evaluator.hybrid import HybridEvaluator
from src.factory import build_judge, generation_config, load_prompt
from src.run_metadata import new_run_id
from src.taxonomy import normalize_error_type


def _type_macro_f1(gold_types: list[str], pred_types: list[str | None]) -> float | None:
    labels = sorted({g for g in gold_types})
    if not labels:
        return None
    f1s: list[float] = []
    for lab in labels:
        tp = sum(1 for g, p in zip(gold_types, pred_types, strict=False) if g == lab and p == lab)
        fp = sum(1 for g, p in zip(gold_types, pred_types, strict=False) if g != lab and p == lab)
        fn = sum(1 for g, p in zip(gold_types, pred_types, strict=False) if g == lab and p != lab)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1s.append(0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec))
    return sum(f1s) / len(f1s)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/processed/adversarial.jsonl")
    parser.add_argument("--provider", choices=["hy3", "mock", "none"], default="hy3")
    parser.add_argument("--method", choices=["B0-DirectJudge", "Full"], default="Full")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--out-dir", default="results")
    parser.add_argument("--max-samples", type=int, default=None)
    args = parser.parse_args(argv)

    items = load_jsonl(args.data)
    if args.max_samples:
        items = items[: args.max_samples]
    if not items:
        print("[adv-eval] no samples")
        return 1

    config = load_config(args.config)
    gen_cfg = generation_config(config)
    judge = None if args.provider == "none" else build_judge(config, args.provider)
    hybrid = HybridEvaluator(judge) if args.method == "Full" else None
    if args.method != "Full" and judge is None:
        print("[adv-eval] B0 requires a judge provider")
        return 1

    run_id = new_run_id(prefix=args.method)
    prompt = load_prompt(config.paths.get("prompts_dir", "prompts"), "direct_judge.md")
    signature = run_signature(
        method=args.method,
        model=config.model or args.provider,
        system_prompt=prompt,
        generation_config=gen_cfg,
    )
    raw_path = Path(args.out_dir) / "raw" / f"{args.method}_adversarial.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    records = []
    with raw_path.open("w", encoding="utf-8") as f:
        for item in items:
            sample = item.to_canonical()
            if hybrid is not None:
                audit = hybrid.audit_sample(sample, **gen_cfg)
                pred = JudgePrediction(
                    sample_id=sample.sample_id,
                    process_correct=audit.process_correct,
                    first_error_step=audit.first_error_step,
                    error_type=audit.error_type,
                    parse_status="SUCCESS" if audit.process_correct is not None else "FAILURE",
                )
                rec = build_raw_record(
                    sample,
                    pred,
                    method=args.method,
                    run_id=run_id,
                    run_signature=signature,
                )
                rec["fused_process_correct"] = audit.process_correct
                rec["fused_first_error_step"] = audit.first_error_step
                rec["fused_error_type"] = audit.error_type
                rec["gold_error_type"] = item.gold_error_type
                rec["answer_preserving"] = item.answer_preserving
            else:
                pred = judge.judge(sample, **gen_cfg)
                rec = build_raw_record(
                    sample, pred, method=args.method, run_id=run_id, run_signature=signature
                )
                rec["fused_process_correct"] = pred.process_correct
                rec["fused_first_error_step"] = pred.first_error_step
                rec["fused_error_type"] = pred.error_type
                rec["gold_error_type"] = item.gold_error_type
                rec["answer_preserving"] = item.answer_preserving
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            records.append(rec)
            print(f"[adv-eval] {item.sample_id} fused={rec['fused_first_error_step']} "
                  f"gold={item.gold_first_error_step}")

    golds = [it.to_canonical() for it in items]
    fused_preds = [
        JudgePrediction(
            sample_id=r["sample_id"],
            process_correct=r.get("fused_process_correct"),
            first_error_step=r.get("fused_first_error_step"),
            error_type=r.get("fused_error_type"),
            parse_status="SUCCESS" if r.get("fused_process_correct") is not None else "FAILURE",
        )
        for r in records
    ]
    metrics = compute_metrics(fused_preds, golds)
    gold_types = [it.gold_error_type for it in items]
    pred_types = [normalize_error_type(r.get("fused_error_type")) for r in records]
    ap = [r for r, it in zip(records, items, strict=False) if it.answer_preserving]
    ap_hits = sum(1 for r in ap if r.get("fused_process_correct") is False)
    payload = {
        "run_id": run_id,
        "method": args.method,
        "n": len(records),
        "metrics": metrics.to_dict(),
        "error_type_macro_f1": _type_macro_f1(gold_types, pred_types),
        "unsupported_recall": (ap_hits / len(ap)) if ap else None,
        "n_answer_preserving": len(ap),
    }
    out = Path(args.out_dir) / "summaries" / f"{args.method}_adversarial_{run_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    official = Path("reports/official/adversarial.json")
    official.parent.mkdir(parents=True, exist_ok=True)
    official.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"[adv-eval] wrote {out} and {official}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
