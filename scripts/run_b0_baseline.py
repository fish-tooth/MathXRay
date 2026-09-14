"""B0 Direct-Judge baseline runner (P1-T08 / EXT-01).

Loads ProcessBench, converts rows to canonical samples, runs the B0 Direct Hy3
judge over a stratified subset, and writes the raw-first artifacts:

    results/raw/B0-DirectJudge_<stage>_<run_id>.jsonl
    results/summaries/B0-DirectJudge_<stage>_<run_id>.json
    results/summaries/B0-DirectJudge_<stage>_<run_id>.md

Metrics are recomputed from the raw file (never from in-memory state) so the
baseline table is reproducible. Resume is on by default and keyed by
``sample_id + method + run_signature``.

Usage:
    python scripts/run_b0_baseline.py --stage smoke
    python scripts/run_b0_baseline.py --stage pilot
    python scripts/run_b0_baseline.py --stage dev
    python scripts/run_b0_baseline.py --stage smoke --provider mock   # offline
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from datasets import load_dataset

from src.analysis.metrics import group_by_source
from src.benchmark.processbench_adapter import to_canonical
from src.benchmark.runner import (
    align_predictions,
    recompute_metrics,
    run_baseline,
    run_signature,
    stratified_sample,
)
from src.config import Config, load_config
from src.evaluator.direct_judge import DirectJudge
from src.llm.hy3_provider import Hy3Provider
from src.llm.mock_provider import MockProvider
from src.run_metadata import make_metadata, new_run_id, stable_hash

DATASET = "Qwen/ProcessBench"
METHOD = "B0-DirectJudge"
STAGE_SIZES = {"smoke": 20, "pilot": 60, "dev": 300}

# Offline mock returns a valid "process correct" prediction so the pipeline can
# be exercised end-to-end without any real API call.
_MOCK_DEFAULT = (
    '{"process_correct": true, "first_error_step": null, '
    '"error_type": null, "reason": "mock"}'
)


def _build_gen_cfg(config: Config) -> dict[str, Any]:
    """Build a deterministic generation config from loaded YAML (drop Nones)."""
    g = config.generation
    gen: dict[str, Any] = {}
    for key in ("temperature", "max_tokens", "reasoning_effort"):
        value = g.get(key)
        if value is not None:
            gen[key] = value
    return gen


def _load_system_prompt(prompts_dir: str | Path) -> str:
    path = Path(prompts_dir) / "direct_judge.md"
    if not path.exists():
        raise FileNotFoundError(f"Missing judge prompt: {path}")
    return path.read_text(encoding="utf-8")


def _build_provider(config: Config, provider_name: str):
    if provider_name == "mock":
        return MockProvider(default=_MOCK_DEFAULT)
    if provider_name != "hy3":
        raise ValueError(f"Unknown provider: {provider_name!r}")

    model = config.model
    if not model:
        raise SystemExit(
            "Hy3 model is not set. Provide HY3_MODEL (or provider.model in YAML) "
            "before running against the real API."
        )
    return Hy3Provider(
        api_key=config.require_api_key(),
        base_url=config.base_url,
        model=model,
        timeout=float(config.generation.get("timeout_seconds", 120)),
        max_retries=int(config.generation.get("max_retries", 3)),
        retry_backoff_base=float(config.generation.get("retry_backoff_base", 2.0)),
        # Deep-thinking runs can return an empty content; retry once at a lower
        # effort to recover the structured answer (see Hy3Provider).
        empty_content_fallback_effort="low",
    )


def _load_rows(max_samples: int, seed: int):
    """Load ProcessBench and return stratified ``(source, row)`` pairs."""
    ds = load_dataset(DATASET, "default")
    rows_by_split = {split: list(ds[split]) for split in ds.keys()}
    return stratified_sample(rows_by_split, max_samples, seed=seed)


def _metrics_summary(metrics) -> dict[str, Any]:
    return {
        "n_all": metrics.n_all,
        "n_gold_error": metrics.n_gold_error,
        "n_gold_correct": metrics.n_gold_correct,
        "error_detection_recall": metrics.error_detection_recall,
        "first_error_exact": metrics.first_error_exact,
        "correct_process_accuracy": metrics.correct_process_accuracy,
        "process_status_accuracy": metrics.process_status_accuracy,
        "official_composite": metrics.official_composite,
        "plus_minus_one": metrics.plus_minus_one,
        "mean_abs_step_distance": metrics.mean_abs_step_distance,
        "n_missed_localization": metrics.n_missed_localization,
        "n_parse_failure": metrics.n_parse_failure,
        "n_api_failure": metrics.n_api_failure,
        "n_pred_missing": metrics.n_pred_missing,
    }


def _render_markdown(summary: dict[str, Any], per_source: dict[str, Any]) -> str:
    def fmt(v):
        if v is None:
            return "-"
        if isinstance(v, float):
            return f"{v:.4f}"
        return str(v)

    lines = ["# B0 Direct-Judge Baseline Summary\n"]
    lines.append("| Metric | Overall |")
    lines.append("|---|---|")
    metric_names = [
        ("error_detection_recall", "Error Detection Recall (M1)"),
        ("first_error_exact", "First-Error Exact Accuracy (M2)"),
        ("correct_process_accuracy", "Correct Process Accuracy (M3)"),
        ("process_status_accuracy", "Process Status Accuracy (M4)"),
        ("official_composite", "Official Composite (M5)"),
        ("plus_minus_one", "+/-1 Localization (aux)"),
        ("mean_abs_step_distance", "Mean Abs Step Distance (aux)"),
    ]
    for key, label in metric_names:
        lines.append(f"| {label} | {fmt(summary[key])} |")
    lines.append("")
    lines.append("| Accounting | Value |")
    lines.append("|---|---|")
    for key, label in [
        ("n_all", "n_all"),
        ("n_gold_error", "n_gold_error"),
        ("n_gold_correct", "n_gold_correct"),
        ("n_parse_failure", "n_parse_failure"),
        ("n_api_failure", "n_api_failure"),
        ("n_pred_missing", "n_pred_missing"),
        ("n_missed_localization", "n_missed_localization"),
    ]:
        lines.append(f"| {label} | {fmt(summary[key])} |")

    if per_source:
        lines.append("\n## Per-source\n")
        lines.append("| Source | M2 First-Error Exact | M3 Correct Acc | M4 Status Acc | n |")
        lines.append("|---|---|---|---|---|")
        for source, m in sorted(per_source.items()):
            lines.append(
                f"| {source} | {fmt(m['first_error_exact'])} | "
                f"{fmt(m['correct_process_accuracy'])} | "
                f"{fmt(m['process_status_accuracy'])} | {fmt(m['n_all'])} |"
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the B0 Direct-Judge baseline.")
    parser.add_argument("--stage", choices=list(STAGE_SIZES), default="smoke")
    parser.add_argument("--provider", choices=["hy3", "mock"], default="hy3")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--out-dir", default="results")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    seed = args.seed if args.seed is not None else config.seed
    max_samples = args.max_samples or STAGE_SIZES[args.stage]
    prompts_dir = config.paths.get("prompts_dir", "prompts")

    system_prompt = _load_system_prompt(prompts_dir)
    provider = _build_provider(config, args.provider)
    model = config.model or ("mock" if args.provider == "mock" else "")
    judge = DirectJudge(provider, system_prompt, model=model)

    # Deterministic run signature + run id.
    gen_cfg = _build_gen_cfg(config)
    signature = run_signature(
        method=METHOD, model=model, system_prompt=system_prompt, generation_config=gen_cfg
    )
    run_id = new_run_id(prefix=METHOD)

    # Load + stratify samples.
    print(f"[run] loading ProcessBench (stage={args.stage}, n={max_samples}, seed={seed})")
    pairs = _load_rows(max_samples, seed)
    samples = [to_canonical(row, source=source) for source, row in pairs]
    print(f"[run] {len(samples)} samples across {len({s.source for s in samples})} sources")

    out_dir = Path(args.out_dir)
    # Raw file is stable across runs (keyed by method + stage) so resume can
    # reuse completed samples; each record still carries its own run_id.
    raw_path = out_dir / "raw" / f"{METHOD}_{args.stage}.jsonl"
    summaries_dir = out_dir / "summaries"

    # Execute (with resume).
    result = run_baseline(
        judge,
        samples,
        method=METHOD,
        run_id=run_id,
        run_signature=signature,
        raw_path=raw_path,
        resume=not args.no_resume,
        generation_config=gen_cfg,
    )
    print(
        f"[run] completed={len(result.records)} new={result.n_new} "
        f"resumed={result.n_resumed}"
    )

    # Recompute metrics from the raw file (raw-first reproducibility).
    overall = recompute_metrics(result.records, samples)
    predictions = align_predictions(result.records, samples)
    per_source = group_by_source(predictions, samples)

    summary = _metrics_summary(overall)
    per_source_dict = {s: _metrics_summary(m) for s, m in per_source.items()}

    # Persist run metadata.
    manifest = [s.sample_id for s in samples]
    metadata = make_metadata(
        run_id=run_id,
        model=model,
        provider=args.provider,
        temperature=float(gen_cfg.get("temperature", 0.0)),
        reasoning_setting=str(gen_cfg.get("reasoning_effort", "")),
        prompt_versions={"direct_judge": stable_hash(system_prompt)},
        config=config.to_dict(),
        dataset_name=DATASET,
        dataset_manifest=manifest,
        seed=seed,
    )
    summaries_dir.mkdir(parents=True, exist_ok=True)
    meta_path = summaries_dir / f"{METHOD}_{args.stage}_{run_id}.meta.json"
    meta_path.write_text(
        json.dumps(metadata.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Summary JSON + Markdown.
    payload = {
        "run_id": run_id,
        "stage": args.stage,
        "method": METHOD,
        "provider": args.provider,
        "model": model,
        "seed": seed,
        "run_signature": signature,
        "config_hash": metadata.config_hash,
        "dataset_manifest_hash": metadata.dataset_manifest_hash,
        "metrics": summary,
        "per_source": per_source_dict,
    }
    json_path = summaries_dir / f"{METHOD}_{args.stage}_{run_id}.json"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    md_path = summaries_dir / f"{METHOD}_{args.stage}_{run_id}.md"
    md_path.write_text(_render_markdown(summary, per_source_dict), encoding="utf-8")

    print(f"[run] raw      -> {raw_path}")
    print(f"[run] summary  -> {json_path}")
    print(f"[run] report   -> {md_path}")
    print("\nMetrics (overall):")
    for key, label in [
        ("error_detection_recall", "M1 Error Detection Recall"),
        ("first_error_exact", "M2 First-Error Exact"),
        ("correct_process_accuracy", "M3 Correct Process Acc"),
        ("process_status_accuracy", "M4 Process Status Acc"),
        ("official_composite", "M5 Official Composite"),
    ]:
        val = summary[key]
        print(f"  {label:<28} {val if val is not None else '-'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
