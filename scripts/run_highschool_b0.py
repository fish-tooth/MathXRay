"""Run B0 Direct Judge on the frozen high-school eval slice."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.analysis.metrics import compute_metrics, group_by_source
from src.benchmark.highschool import load_eval_jsonl, pb_harmonic_f1
from src.benchmark.runner import (
    align_predictions,
    recompute_metrics,
    run_baseline,
    run_signature,
)
from src.config import Config, load_config
from src.evaluator.direct_judge import DirectJudge
from src.llm.hy3_provider import Hy3Provider
from src.llm.mock_provider import MockProvider
from src.run_metadata import make_metadata, new_run_id, stable_hash

METHOD = "B0-HighSchool"
_MOCK_DEFAULT = (
    '{"process_correct": true, "first_error_step": null, '
    '"error_type": null, "reason": "mock"}'
)


def _build_gen_cfg(config: Config) -> dict[str, Any]:
    g = config.generation
    gen: dict[str, Any] = {}
    for key in ("temperature", "max_tokens", "reasoning_effort"):
        value = g.get(key)
        if value is not None:
            gen[key] = value
    return gen


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


def _build_provider(config: Config, provider_name: str):
    if provider_name == "mock":
        return MockProvider(default=_MOCK_DEFAULT)
    if provider_name != "hy3":
        raise ValueError(f"Unknown provider: {provider_name!r}")
    model = config.model
    if not model:
        raise SystemExit("HY3_MODEL is not set.")
    return Hy3Provider(
        api_key=config.require_api_key(),
        base_url=config.base_url,
        model=model,
        timeout=float(config.generation.get("timeout_seconds", 120)),
        max_retries=int(config.generation.get("max_retries", 3)),
        retry_backoff_base=float(config.generation.get("retry_backoff_base", 2.0)),
        empty_content_fallback_effort="low",
    )


def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def _track_of(sample) -> str:
    return str((sample.metadata or {}).get("track") or sample.source)


def _analyze(records, samples) -> dict[str, Any]:
    by_track: dict[str, list] = {}
    golds_by_track: dict[str, list] = {}
    for sample in samples:
        track = _track_of(sample)
        golds_by_track.setdefault(track, []).append(sample)
    aligned = align_predictions(records, samples)
    for pred, sample in zip(aligned, samples, strict=False):
        by_track.setdefault(_track_of(sample), []).append(pred)

    tracks = {}
    for track, golds in golds_by_track.items():
        if track == "qwen_right":
            continue
        preds = by_track.get(track, [])
        tracks[track] = _metrics_summary(compute_metrics(preds, golds))

    qwen_right_preds = by_track.get("qwen_right") or []
    n_right = len(golds_by_track.get("qwen_right") or [])
    n_flagged = sum(1 for p in qwen_right_preds if p and p.process_correct is False)
    n_accepted = sum(1 for p in qwen_right_preds if p and p.process_correct is True)

    official = tracks.get("official") or {}
    adv = tracks.get("adversarial") or {}
    probe_f1 = pb_harmonic_f1(adv.get("first_error_exact"), official.get("correct_process_accuracy"))
    return {
        "tracks": tracks,
        "processbench_probe_f1": probe_f1,
        "qwen_right_unsupported_candidates": {
            "n": n_right,
            "pred_process_incorrect": n_flagged,
            "pred_process_correct": n_accepted,
            "flag_rate": (n_flagged / n_right) if n_right else None,
        },
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# High-school B0 Direct-Judge\n"]
    lines.append(
        "Gold 口径：`qwen_wrong` 仅支持 M1；`official` 支持 M3；"
        "`adversarial` 支持 M1/M2；`qwen_right` 无过程金标准。\n"
    )
    f1 = payload.get("processbench_probe_f1")
    lines.append(f"ProcessBench-style F1（adversarial M2 与 official M3 的调和平均）：**{_fmt(f1)}**\n")
    lines.append("| Track | n | M1 | M2 | M3 | M4 | parse_fail |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for track, m in sorted((payload.get("tracks") or {}).items()):
        lines.append(
            f"| {track} | {m['n_all']} | {_fmt(m['error_detection_recall'])} | "
            f"{_fmt(m['first_error_exact'])} | {_fmt(m['correct_process_accuracy'])} | "
            f"{_fmt(m['process_status_accuracy'])} | {m['n_parse_failure']} |"
        )
    uns = payload.get("qwen_right_unsupported_candidates") or {}
    lines.append("\n## Answer-correct Qwen traces (unlabeled process)\n")
    lines.append(
        f"n={uns.get('n')} · flagged process-invalid={uns.get('pred_process_incorrect')} "
        f"({_fmt(uns.get('flag_rate'))}) · accepted={uns.get('pred_process_correct')}"
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["smoke", "pilot"], default="pilot")
    parser.add_argument("--provider", choices=["hy3", "mock"], default="hy3")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--eval-path", default=None)
    parser.add_argument("--out-dir", default="results")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args(argv)

    eval_path = Path(args.eval_path or f"data/processed/highschool_{args.stage}.jsonl")
    if not eval_path.exists():
        raise SystemExit(f"Missing {eval_path}. Run scripts/prepare_highschool.py --stage {args.stage}")

    config = load_config(args.config)
    system_prompt = Path(config.paths.get("prompts_dir", "prompts"), "direct_judge.md").read_text(
        encoding="utf-8"
    )
    provider = _build_provider(config, args.provider)
    model = config.model or ("mock" if args.provider == "mock" else "")
    judge = DirectJudge(provider, system_prompt, model=model)
    gen_cfg = _build_gen_cfg(config)
    signature = run_signature(
        method=METHOD, model=model, system_prompt=system_prompt, generation_config=gen_cfg,
        provider=args.provider,
    )
    run_id = new_run_id(prefix=METHOD)
    samples = load_eval_jsonl(eval_path)

    out_dir = Path(args.out_dir)
    raw_path = out_dir / "raw" / f"{METHOD}_{args.stage}.jsonl"
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
    print(f"[run] completed={len(result.records)} new={result.n_new} resumed={result.n_resumed}")

    overall = recompute_metrics(result.records, samples)
    predictions = align_predictions(result.records, samples)
    per_source = group_by_source(predictions, samples)
    extra = _analyze(result.records, samples)

    metadata = make_metadata(
        run_id=run_id,
        model=model,
        provider=args.provider,
        temperature=float(gen_cfg.get("temperature", 0.0)),
        reasoning_setting=str(gen_cfg.get("reasoning_effort", "")),
        prompt_versions={"direct_judge": stable_hash(system_prompt)},
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
