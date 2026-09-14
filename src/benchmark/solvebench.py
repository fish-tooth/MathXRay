"""SolveBench adapter: GSM8K / MATH / Omni-MATH with frozen D1–D5 mapping (R5)."""

from __future__ import annotations

import json
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DATASET_VERSION = "solvebench-v1"
LICENSE = {
    "gsm8k": "MIT (openai/gsm8k)",
    "math": "MIT (hendrycks/competition_math)",
    "omnimath": "CC-BY-SA / dataset card of Omni-MATH",
}

# Frozen mapping (must not be changed after formal freeze).
# D1 GSM8K, D2 MATH-1/2, D3 MATH-3, D4 MATH-4/5, D5 Omni-MATH.
SOURCE_TO_DEFAULT_DIFFICULTY = {
    "gsm8k": "D1",
    "math": None,  # filled from official level
    "omnimath": "D5",
}


@dataclass
class SolveSample:
    sample_id: str
    problem: str
    gold_answer: str
    source: str
    source_split: str
    difficulty: str
    answer_type: str = "numeric"
    verification_strategy: str = "auto"
    license_or_citation: str = ""
    dataset_version: str = DATASET_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_gsm8k_answer(raw: str) -> str:
    if "####" in raw:
        return raw.split("####")[-1].strip().replace(",", "")
    return raw.strip()


def extract_boxed(text: str) -> str:
    """Extract the last \\boxed{...} value, supporting one level of nesting."""
    key = r"\boxed{"
    start = text.rfind(key)
    if start == -1:
        # Some MATH solutions use \boxed 42 without braces.
        m = re.search(r"\\boxed\s+([^\s$]+)", text)
        return m.group(1).strip() if m else text.strip()
    i = start + len(key)
    depth = 1
    chars: list[str] = []
    while i < len(text) and depth:
        ch = text[i]
        if ch == "{":
            depth += 1
            chars.append(ch)
        elif ch == "}":
            depth -= 1
            if depth:
                chars.append(ch)
        else:
            chars.append(ch)
        i += 1
    return "".join(chars).strip()


def math_level_to_difficulty(level: Any) -> str:
    raw = str(level).strip().lower().replace("level ", "")
    try:
        n = int(raw)
    except ValueError:
        return "D3"
    if n <= 2:
        return "D2"
    if n == 3:
        return "D3"
    return "D4"


def infer_answer_type(answer: str) -> str:
    s = answer.strip()
    if re.fullmatch(r"-?\d+", s):
        return "integer"
    if re.fullmatch(r"-?\d+/\d+", s) or re.fullmatch(r"-?\d+(?:\.\d+)?", s):
        return "numeric"
    if "," in s or s.startswith("{") or "\\pm" in s or "±" in s:
        return "set"
    return "symbolic"


def from_gsm8k(row: dict[str, Any], idx: int, split: str) -> SolveSample:
    gold = extract_gsm8k_answer(str(row.get("answer") or ""))
    return SolveSample(
        sample_id=f"gsm8k-{split}-{idx}",
        problem=str(row["question"]),
        gold_answer=gold,
        source="gsm8k",
        source_split=split,
        difficulty="D1",
        answer_type=infer_answer_type(gold),
        verification_strategy="numeric",
        license_or_citation=LICENSE["gsm8k"],
    )


def from_math(row: dict[str, Any], idx: int, split: str) -> SolveSample:
    gold = extract_boxed(str(row.get("solution") or row.get("answer") or ""))
    level = row.get("level") or row.get("difficulty") or ""
    return SolveSample(
        sample_id=f"math-{split}-{idx}",
        problem=str(row.get("problem") or row.get("question") or ""),
        gold_answer=gold,
        source="math",
        source_split=str(row.get("type") or split),
        difficulty=math_level_to_difficulty(level),
        answer_type=infer_answer_type(gold),
        verification_strategy="auto",
        license_or_citation=LICENSE["math"],
    )


def from_omnimath(row: dict[str, Any], idx: int, split: str) -> SolveSample:
    gold = str(row.get("answer") or extract_boxed(str(row.get("solution") or "")))
    return SolveSample(
        sample_id=f"omnimath-{split}-{idx}",
        problem=str(row.get("problem") or row.get("question") or ""),
        gold_answer=gold,
        source="omnimath",
        source_split=str(row.get("domain") or split),
        difficulty="D5",
        answer_type=infer_answer_type(gold),
        verification_strategy="auto",
        license_or_citation=LICENSE["omnimath"],
    )


def stratified_by_difficulty(
    samples: list[SolveSample],
    n: int,
    *,
    seed: int,
) -> list[SolveSample]:
    rng = random.Random(seed)
    buckets: dict[str, list[SolveSample]] = {}
    for s in samples:
        buckets.setdefault(s.difficulty, []).append(s)
    names = sorted(buckets)
    if not names or n <= 0:
        return []
    per = max(1, n // len(names))
    chosen: list[SolveSample] = []
    leftover: list[SolveSample] = []
    for name in names:
        pool = list(buckets[name])
        rng.shuffle(pool)
        take = min(per, len(pool))
        chosen.extend(pool[:take])
        leftover.extend(pool[take:])
    rng.shuffle(leftover)
    while len(chosen) < n and leftover:
        chosen.append(leftover.pop())
    rng.shuffle(chosen)
    return chosen[:n]


def dump_jsonl(path: str | Path, samples: list[SolveSample]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s.to_dict(), ensure_ascii=False) + "\n")
    return path


def load_jsonl(path: str | Path) -> list[SolveSample]:
    samples: list[SolveSample] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            samples.append(SolveSample(**json.loads(line)))
    return samples
