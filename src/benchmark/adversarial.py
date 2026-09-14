"""TraceAdversarialBench: deterministic mutations of gold-correct traces (M11)."""

from __future__ import annotations

import json
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.benchmark.processbench_adapter import CanonicalSample

NUMBER = re.compile(r"(?<![\w.])(-?\d+(?:\.\d+)?)(?![\w.])")

MUTATION_TO_TYPE = {
    "arithmetic": "ARITHMETIC_ERROR",
    "sign": "ARITHMETIC_ERROR",
    "operator": "ALGEBRA_ERROR",
    "unused_claim": "HALLUCINATION",
}


@dataclass
class AdversarialSample:
    sample_id: str
    problem: str
    steps: list[str]
    source: str
    source_id: str
    mutation: str
    mutation_step: int
    gold_process_correct: bool
    gold_first_error_step: int | None
    gold_error_type: str
    gold_final_answer_correct: bool
    answer_preserving: bool
    seed: int
    version: str = "tab-v1"

    def to_canonical(self) -> CanonicalSample:
        return CanonicalSample(
            sample_id=self.sample_id,
            problem=self.problem,
            steps=self.steps,
            source=self.source,
            gold_process_correct=self.gold_process_correct,
            gold_first_error_step=self.gold_first_error_step,
            gold_final_answer_correct=self.gold_final_answer_correct,
            metadata={
                "mutation": self.mutation,
                "gold_error_type": self.gold_error_type,
                "answer_preserving": self.answer_preserving,
                "source_id": self.source_id,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _perturb_number(token: str) -> str | None:
    if "." in token:
        value = float(token)
        nxt = value + (1.0 if value >= 0 else -1.0)
        return str(int(nxt)) if nxt.is_integer() else str(nxt)
    value = int(token)
    nxt = value + 1 if value >= 0 else value - 1
    if str(nxt) == token:
        nxt = value + 2
    return str(nxt)


def mutate_arithmetic(step: str) -> str | None:
    matches = list(NUMBER.finditer(step))
    if not matches:
        return None
    m = matches[-1]
    nxt = _perturb_number(m.group(1))
    if nxt is None or nxt == m.group(1):
        return None
    return step[: m.start()] + nxt + step[m.end() :]


def mutate_sign(step: str) -> str | None:
    if " + " in step:
        return step.replace(" + ", " - ", 1)
    if " - " in step:
        return step.replace(" - ", " + ", 1)
    if "+" in step:
        return step.replace("+", "-", 1)
    if "-" in step[1:]:
        idx = step.find("-", 1)
        return step[:idx] + "+" + step[idx + 1 :]
    return None


def mutate_operator(step: str) -> str | None:
    if "*" in step:
        return step.replace("*", "+", 1)
    if "×" in step:
        return step.replace("×", "+", 1)
    if "/" in step:
        return step.replace("/", "-", 1)
    if " + " in step:
        return step.replace(" + ", " * ", 1)
    return None


def mutate_unused_claim(step: str) -> str:
    return step.rstrip() + " Also, 2 + 2 = 5."


MUTATORS = {
    "arithmetic": mutate_arithmetic,
    "sign": mutate_sign,
    "operator": mutate_operator,
}


def mutate_trace(
    sample: CanonicalSample,
    *,
    mutation: str,
    rng: random.Random,
    seed: int,
) -> AdversarialSample | None:
    if not sample.steps:
        return None
    # Prefer a middle step so localization is non-trivial.
    indices = list(range(len(sample.steps)))
    rng.shuffle(indices)
    for idx in indices:
        original = sample.steps[idx]
        if mutation == "unused_claim":
            mutated = mutate_unused_claim(original)
        else:
            fn = MUTATORS[mutation]
            mutated = fn(original)
        if not mutated or mutated == original:
            continue
        steps = list(sample.steps)
        steps[idx] = mutated
        answer_preserving = mutation == "unused_claim"
        return AdversarialSample(
            sample_id=f"{sample.sample_id}::{mutation}::s{idx + 1}",
            problem=sample.problem,
            steps=steps,
            source=sample.source,
            source_id=sample.sample_id,
            mutation=mutation,
            mutation_step=idx + 1,
            gold_process_correct=False,
            gold_first_error_step=idx + 1,
            gold_error_type=MUTATION_TO_TYPE[mutation],
            gold_final_answer_correct=bool(sample.gold_final_answer_correct)
            if answer_preserving
            else False,
            answer_preserving=answer_preserving,
            seed=seed,
        )
    return None


def build_adversarial(
    correct_samples: list[CanonicalSample],
    *,
    n: int,
    seed: int,
    mutations: tuple[str, ...] = ("arithmetic", "sign", "operator", "unused_claim"),
) -> list[AdversarialSample]:
    rng = random.Random(seed)
    pool = [s for s in correct_samples if s.gold_process_correct and s.steps]
    rng.shuffle(pool)
    out: list[AdversarialSample] = []
    mut_cycle = list(mutations)
    i = 0
    for sample in pool:
        if len(out) >= n:
            break
        mutation = mut_cycle[i % len(mut_cycle)]
        i += 1
        item = mutate_trace(sample, mutation=mutation, rng=rng, seed=seed)
        if item is not None:
            out.append(item)
    return out[:n]


def dump_jsonl(path: str | Path, samples: list[AdversarialSample]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s.to_dict(), ensure_ascii=False) + "\n")
    return path


def load_jsonl(path: str | Path) -> list[AdversarialSample]:
    rows: list[AdversarialSample] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(AdversarialSample(**json.loads(line)))
    return rows
