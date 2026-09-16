"""Run the reflective critic on the frozen high-school eval slice."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from run_highschool_b0 import _analyze, _metrics_summary, _render_markdown

from src.analysis.metrics import group_by_source
from src.benchmark.highschool import load_eval_jsonl
from src.benchmark.runner import (
    align_predictions,
    recompute_metrics,
    run_baseline,
    run_signature,
)
from src.config import load_config
from src.factory import build_reflective, generation_config
from src.run_metadata import make_metadata, new_run_id, stable_hash

METHOD = "R1-ReflectiveCritic"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["smoke", "pilot"], default="smoke")
    parser.add_argument("--provider", choices=["hy3", "mock"], default="hy3")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--eval-path", default=None)
    parser.add_argument("--out-dir", default="results")
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--max-samples", type=int, default=None)
    args = parser.parse_args(argv)

    eval_path = Path(args.eval_path or f"data/processed/highschool_{args.stage}.jsonl")
    if not eval_path.exists():
        raise SystemExit(f"Missing {eval_path}. Run scripts/prepare_highschool.py --stage {args.stage}")

    config = load_config(args.config)
    critic = build_reflective(config, args.provider, answer_aware=True)
    model = config.model or ("mock" if args.provider == "mock" else "")
    gen_cfg = generation_config(config)
    prompts_dir = Path(config.paths.get("prompts_dir", "prompts"))
    prompt_blob = "".join(
        (prompts_dir / name).read_text(encoding="utf-8")
        for name in (
            "independent_solve.md",
            "stepwise_critic.md",
            "accuser.md",
            "defender.md",
            "arbiter.md",
        )
    )
    signature = run_signature(
        method=METHOD, model=model, system_prompt=prompt_blob, generation_config=gen_cfg,
        provider=args.provider,
    )
    run_id = new_run_id(prefix=METHOD)
    samples = load_eval_jsonl(eval_path)
    if args.max_samples:
        samples = samples[: args.max_samples]
    print(f"[run] {METHOD} n={len(samples)} answer_aware=True")

    out_dir = Path(args.out_dir)
    raw_path = out_dir / "raw" / f"{METHOD}_{args.stage}.jsonl"
    result = run_baseline(
        critic,
        samples,
        method=METHOD,
        run_id=run_id,
        run_signature=signature,
        raw_path=raw_path,
        resume=not args.no_resume,
        generation_config=gen_cfg,
    )
    print(f"[run] completed={len(result.records)} new={result.n_new} resumed={result.n_resumed}")

    overall = recompute_metrics(result.records, samples)
    predictions = align_predictions(result.records, samples)
    per_source = group_by_source(predictions, samples)
    extra = _analyze(result.records, samples)
    n_debate = sum(
        1
        for rec in result.records
        if (rec.get("prediction") or {}).get("extra", {}).get("debate_triggered")
    )
    n_calls = [
        (rec.get("prediction") or {}).get("retry_count")
        for rec in result.records
        if (rec.get("prediction") or {}).get("retry_count")
    ]
    metadata = make_metadata(
        run_id=run_id,
        model=model,
        provider=args.provider,
        temperature=float(gen_cfg.get("temperature", 0.0)),
        reasoning_setting=str(gen_cfg.get("reasoning_effort", "")),
        prompt_versions={"reflective": stable_hash(prompt_blob)},
        config=config.to_dict(),
        dataset_name="high_school_private",
        dataset_manifest=[s.sample_id for s in samples],
        seed=42,
    )
    payload = {
        "run_id": run_id,
        "stage": args.stage,
        "method": METHOD,
        "provider": args.provider,
        "model": model,
        "run_signature": signature,
        "eval_path": str(eval_path),
        "n_debate": n_debate,
        "calls_per_sample_mean": (sum(n_calls) / len(n_calls)) if n_calls else None,
        "metrics_mixed_do_not_cite": _metrics_summary(overall),
        "per_source": {s: _metrics_summary(m) for s, m in per_source.items()},
        **extra,
        "dataset_manifest_hash": metadata.dataset_manifest_hash,
    }
    summaries = out_dir / "summaries"
    summaries.mkdir(parents=True, exist_ok=True)
    json_path = summaries / f"{METHOD}_{args.stage}_{run_id}.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path = summaries / f"{METHOD}_{args.stage}_{run_id}.md"
    md_path.write_text(_render_markdown(payload), encoding="utf-8")
    print(_render_markdown(payload))
    print(f"[run] raw -> {raw_path}")
    print(f"[run] summary -> {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
