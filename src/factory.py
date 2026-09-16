"""Shared constructors for providers, solver, and judges."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.config import Config
from src.evaluator.direct_judge import DirectJudge
from src.evaluator.hybrid import HybridEvaluator
from src.evaluator.reflective import ReflectiveCritic
from src.llm.hy3_provider import Hy3Provider
from src.llm.mock_provider import MockProvider
from src.solver.math_solver import MathSolver

_MOCK_JUDGE = (
    '{"process_correct": true, "first_error_step": null, '
    '"error_type": null, "reason": "mock"}'
)
_MOCK_SOLVE = (
    '{"problem": "mock", "solution_steps": ['
    '{"step_id": 1, "statement": "mock step", "expression": "1+1=2", "depends_on": []}'
    '], "final_answer": "2"}'
)
_MOCK_REFLECTIVE = (
    '{"final_answer": "2", "outline": ["1+1=2"], '
    '"steps": [{"step_id": 1, "verdict": "VALID", "claim": "ok", "error_type": null}], '
    '"reason": "mock", "charge_stands": false, "rebuts": false, '
    '"process_correct": true, "first_error_step": null}'
)


def generation_config(config: Config) -> dict[str, Any]:
    gen: dict[str, Any] = {}
    for key in ("temperature", "max_tokens", "reasoning_effort"):
        value = config.generation.get(key)
        if value is not None:
            gen[key] = value
    return gen


def load_prompt(prompts_dir: str | Path, name: str) -> str:
    path = Path(prompts_dir) / name
    if not path.exists():
        raise FileNotFoundError(f"Missing prompt: {path}")
    return path.read_text(encoding="utf-8")


def build_provider(config: Config, provider_name: str = "hy3"):
    if provider_name == "mock":
        return MockProvider(default=_MOCK_JUDGE)
    if provider_name != "hy3":
        raise ValueError(f"Unknown provider: {provider_name!r}")
    model = config.model
    if not model:
        raise SystemExit(
            "Hy3 model is not set. Provide HY3_MODEL (or provider.model in YAML)."
        )
    return Hy3Provider(
        api_key=config.require_api_key(),
        base_url=config.base_url,
        model=model,
        timeout=float(config.generation.get("timeout_seconds", 120)),
        max_retries=int(config.generation.get("max_retries", 3)),
        retry_backoff_base=float(config.generation.get("retry_backoff_base", 2.0)),
        empty_content_fallback_effort="low",
    )


def build_solver(config: Config, provider_name: str = "hy3") -> MathSolver:
    prompts_dir = config.paths.get("prompts_dir", "prompts")
    provider = (
        MockProvider(default=_MOCK_SOLVE)
        if provider_name == "mock"
        else build_provider(config, provider_name)
    )
    return MathSolver(provider, load_prompt(prompts_dir, "solver.md"))


def build_judge(config: Config, provider_name: str = "hy3") -> DirectJudge:
    prompts_dir = config.paths.get("prompts_dir", "prompts")
    provider = build_provider(config, provider_name)
    model = config.model or ("mock" if provider_name == "mock" else "")
    return DirectJudge(provider, load_prompt(prompts_dir, "direct_judge.md"), model=model)


def build_reflective(config: Config, provider_name: str = "hy3", *, answer_aware: bool = False) -> ReflectiveCritic:
    prompts_dir = config.paths.get("prompts_dir", "prompts")
    provider = (
        MockProvider(default=_MOCK_REFLECTIVE)
        if provider_name == "mock"
        else build_provider(config, provider_name)
    )
    model = config.model or ("mock" if provider_name == "mock" else "")
    names = (
        "independent_solve.md",
        "stepwise_critic.md",
        "accuser.md",
        "defender.md",
        "arbiter.md",
    )
    prompts = {Path(name).stem: load_prompt(prompts_dir, name) for name in names}
    return ReflectiveCritic(provider, prompts, model=model, answer_aware=answer_aware)


def build_hybrid(config: Config, provider_name: str = "hy3") -> HybridEvaluator:
    return HybridEvaluator(build_judge(config, provider_name))
