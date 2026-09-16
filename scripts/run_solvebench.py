"""Run Hy3 Solver + answer verifier + process audit on SolveBench."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.benchmark.solvebench import load_jsonl
from src.config import load_config
from src.factory import build_hybrid, build_solver, generation_config
from src.pipeline import MathXRayPipeline
from src.run_metadata import new_run_id
from src.verifier.answer_verifier import Verdict


def _rate(num: int, den: int) -> float | None:
    return num / den if den else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="data/processed/solvebench.jsonl")
    parser.add_argument("--provider", choices=["hy3", "mock"], default="hy3")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--out-dir", default="results")
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args(argv)

    samples = load_jsonl(args.data)
    if args.max_samples:
        samples = samples[: args.max_samples]
    if not samples:
        print(f"[solvebench] no samples in {args.data}")
        return 1

    config = load_config(args.config)
    pipeline = MathXRayPipeline(
        build_solver(config, args.provider),
        build_hybrid(config, args.provider),
    )
    gen_cfg = generation_config(config)
    run_id = new_run_id(prefix="SolveBench")
    raw_path = Path(args.out_dir) / "raw" / "SolveBench.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    done: set[str] = set()
    existing: list[dict] = []
    if not args.no_resume and raw_path.exists():
        for line in raw_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            existing.append(rec)
            if rec.get("parse_status") == "SUCCESS" and rec.get("error") is None:
                done.add(rec["sample_id"])

    n_new = 0
    with raw_path.open("a", encoding="utf-8") as f:
        for sample in samples:
            if sample.sample_id in done:
                continue
            result = pipeline.run(
                sample.problem,
                gold_answer=sample.gold_answer,
                sample_id=sample.sample_id,
                gen_cfg=gen_cfg,
            )
            rec = {
                "sample_id": sample.sample_id,
                "source": sample.source,
                "difficulty": sample.difficulty,
                "gold_answer": sample.gold_answer,
                "run_id": run_id,
                "parse_status": result.solver.parse_status,
                "error": result.solver.error,
                "final_answer": (
                    result.solver.solution.final_answer if result.solver.solution else None
                ),
                "answer_verdict": result.answer.verdict if result.answer else None,
                "answer_strategy": result.answer.strategy if result.answer else None,
                "process_correct": (
                    result.audit.process_correct if result.audit else None
                ),
                "first_error_step": (
                    result.audit.first_error_step if result.audit else None
                ),
                "error_type": result.audit.error_type if result.audit else None,
                "unsupported_answer": result.unsupported_answer,
                "latency_ms": result.solver.latency_ms,
                "result": result.to_dict(),
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            existing.append(rec)
            n_new += 1
            print(f"[solvebench] {sample.sample_id} answer={rec['answer_verdict']} "
                  f"process={rec['process_correct']}")

    # Metrics from the file contents covering this sample list.
    by_id = {r["sample_id"]: r for r in existing}
    aligned = [by_id[s.sample_id] for s in samples if s.sample_id in by_id]
    n = len(aligned)
    n_eq = sum(1 for r in aligned if r.get("answer_verdict") == Verdict.EQUIVALENT)
    n_unknown = sum(1 for r in aligned if r.get("answer_verdict") == Verdict.UNKNOWN)
    n_parse = sum(1 for r in aligned if r.get("parse_status") != "SUCCESS")
    n_flag = sum(1 for r in aligned if r.get("process_correct") is False)
    n_unsup = sum(1 for r in aligned if r.get("unsupported_answer"))

    by_diff: dict[str, list] = {}
    by_src: dict[str, list] = {}
    for s, r in zip((s for s in samples if s.sample_id in by_id), aligned, strict=False):
        by_diff.setdefault(s.difficulty, []).append(r)
        by_src.setdefault(s.source, []).append(r)

    def acc(rows: list) -> float | None:
        return _rate(
            sum(1 for r in rows if r.get("answer_verdict") == Verdict.EQUIVALENT),
            len(rows),
        )

    payload = {
        "run_id": run_id,
        "n": n,
        "n_new": n_new,
        "final_answer_accuracy": _rate(n_eq, n),
        "unknown_rate": _rate(n_unknown, n),
        "parse_failure_rate": _rate(n_parse, n),
        "process_issue_flag_rate": _rate(n_flag, n),
        "n_unsupported_answer": n_unsup,
        "by_difficulty": {d: {"n": len(v), "final_answer_accuracy": acc(v)} for d, v in sorted(by_diff.items())},
        "by_source": {s: {"n": len(v), "final_answer_accuracy": acc(v)} for s, v in sorted(by_src.items())},
        "note": (
            "process_issue_flag_rate is NOT process accuracy; SolveBench has no "
            "independent process gold."
        ),
    }
    out = Path(args.out_dir) / "summaries" / f"SolveBench_{run_id}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
