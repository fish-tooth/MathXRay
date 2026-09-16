"""Adapter for the private high-school math corpus.

The JSON is *not* ProcessBench: it has official answers + textbook analysis and
LLM-generated ``Solution_Steps``, but **no expert first-error labels**.

Tracks (ProcessBench construction, adapted honestly):

- ``qwen_wrong``: LLM trace whose extracted answer ≠ gold. Process is treated as
  invalid (ProcessBench discards the reverse). First-error gold is unknown → M1
  only, never M2.
- ``qwen_right``: LLM trace whose extracted answer matches gold. Process gold is
  unlabeled (answer-correct ⇏ process-correct). Judge still runs; report
  unsupported-answer *candidates* only.
- ``official``: textbook ``analysis`` segmented into steps. Weak gold-correct
  process for M3 / false-positive rate.
- ``adversarial``: deterministic mutations of official traces. Programmatic
  first-error gold → M1/M2.
"""

from __future__ import annotations

import json
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.benchmark.adversarial import build_adversarial
from src.benchmark.processbench_adapter import CanonicalSample
from src.benchmark.solvebench import extract_boxed
from src.verifier.answer_verifier import Verdict, VerdictResult, verify

DEFAULT_PATH = Path("data/high_school_all_annotated_final.json")
GENERATOR_FIELD = "step_by_step_solution_gpt4o"

DIFFICULTY_TO_D = {
    "容易": "D1",
    "较易": "D2",
    "一般": "D3",
    "较难": "D4",
    "困难": "D5",
}

ANSWER_PREFIX = re.compile(
    r"^(?:故选|选项为|正确选项为|正确答案为|正确的命题为|答案是|答案为|解得|因此|所以)[：:\s]*"
)
LETTER_TAIL = re.compile(
    r"(?:故选|选项为|正确选项为|正确答案为|正确的命题为|答案是|答案为)"
    r"[：:\s]*([A-Ga-g]{1,6})"
)
LETTER_ONLY = re.compile(r"^[A-Ga-g]{1,6}$")
LAST_EQ = re.compile(r"=\s*([^=\n]+)\s*$")


@dataclass
class HighSchoolItem:
    ques_id: str
    problem: str
    steps: list[str]
    analysis_steps: list[str]
    qtype: str
    difficulty: str
    gold_answers: list[str]
    option_map: dict[str, str]
    extracted_pred: str | None
    answer_verdict: str
    answer_strategy: str | None
    knowledge: list[str]

    @property
    def answer_correct(self) -> bool | None:
        if self.answer_verdict == Verdict.EQUIVALENT:
            return True
        if self.answer_verdict == Verdict.NOT_EQUIVALENT:
            return False
        return None


def load_raw(path: str | Path = DEFAULT_PATH) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return list(data.values())
    if isinstance(data, list):
        return data
    raise ValueError(f"Unexpected JSON root type: {type(data)!r}")


def option_map(raw: Any) -> dict[str, str]:
    mapping: dict[str, str] = {}
    blocks = raw if isinstance(raw, list) else []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        for item in block.get("option_values") or []:
            key = str(item.get("key") or "").strip().upper()
            val = str(item.get("value") or "").strip()
            if key and val:
                mapping[key] = val
    return mapping


def format_problem(content: str, mapping: dict[str, str], qtype: str) -> str:
    text = (content or "").strip()
    if qtype == "选择" and mapping:
        opts = "\n".join(f"{k}. {v}" for k, v in mapping.items())
        return f"{text}\n\n选项：\n{opts}"
    return text


def gold_answer_candidates(raw_answers: Any, mapping: dict[str, str]) -> list[str]:
    out: list[str] = []
    for item in raw_answers or []:
        for part in str(item).split("##"):
            part = part.strip()
            if not part:
                continue
            out.append(part)
            cleaned = re.sub(r"^\$+|\$+$", "", part).strip()
            if cleaned and cleaned not in out:
                out.append(cleaned)
    extras: list[str] = []
    for g in out:
        letters = g.replace(" ", "").upper()
        if LETTER_ONLY.fullmatch(letters):
            extras.append(letters)
            if len(letters) == 1 and letters in mapping:
                extras.append(mapping[letters])
            elif len(letters) > 1:
                extras.append("".join(mapping[ch] for ch in letters if ch in mapping))
    for e in extras:
        if e and e not in out:
            out.append(e)
    return out


def latex_skeleton(text: str) -> str:
    s = (text or "").strip()
    s = s.replace("$$", "").replace("$", "")
    s = s.replace(r"\(", "").replace(r"\)", "")
    s = s.replace(r"\[", "").replace(r"\]", "")
    s = s.replace("{", "").replace("}", "").replace(" ", "")
    s = s.replace(r"\times", "*").replace(r"\cdot", "*")
    s = s.replace(r"\left", "").replace(r"\right", "")
    s = s.replace("\\", "")
    return s.lower()


def analysis_to_steps(analysis: str) -> list[str]:
    text = analysis or ""
    if "【详解】" in text:
        text = text.split("【详解】", 1)[1]
    elif "详解" in text:
        text = text.split("详解", 1)[-1]
    text = text.strip()
    parts = [p.strip() for p in re.split(r"(?<=[。；;])", text) if p.strip()]
    parts = [p for p in parts if len(p) >= 4]
    return parts or ([text] if text else [])


def extract_pred_answer(steps: list[str], mapping: dict[str, str]) -> str | None:
    if not steps:
        return None
    blob = "\n".join(steps[-2:])
    if r"\boxed" in blob:
        boxed = extract_boxed(blob)
        if boxed and boxed != blob.strip():
            return boxed.strip()
    m = LETTER_TAIL.search(blob)
    if m:
        return m.group(1).upper()
    last = ANSWER_PREFIX.sub("", steps[-1].strip()).strip()
    if LETTER_ONLY.fullmatch(last.replace(" ", "")):
        return last.replace(" ", "").upper()
    eq = LAST_EQ.search(last.replace("$$", "").replace("$", ""))
    if eq:
        last = eq.group(1).strip().rstrip("。.;；")
    skel = latex_skeleton(last)
    for key, val in mapping.items():
        if not val:
            continue
        if latex_skeleton(val) == skel or (len(val) >= 2 and val in blob):
            return key
    return last or None


def match_answers(
    pred: str | None, golds: list[str], mapping: dict[str, str]
) -> VerdictResult:
    if not pred or not golds:
        return VerdictResult(Verdict.PARSE_ERROR, evidence="missing pred or gold")
    cands = [pred]
    letters = pred.replace(" ", "").upper()
    if LETTER_ONLY.fullmatch(letters):
        cands.append(letters)
        if len(letters) == 1 and letters in mapping:
            cands.append(mapping[letters])
        elif len(letters) > 1:
            joined = "".join(mapping[ch] for ch in letters if ch in mapping)
            if joined:
                cands.append(joined)
    for key, val in mapping.items():
        if verify(pred, val).is_equivalent:
            cands.append(key)
    seen: set[str] = set()
    last = VerdictResult(Verdict.UNKNOWN, evidence="no strategy decided")
    gold_skels = {latex_skeleton(g) for g in golds if latex_skeleton(g)}
    for cand in cands:
        if cand in seen:
            continue
        seen.add(cand)
        cand_skel = latex_skeleton(cand)
        if cand_skel and cand_skel in gold_skels:
            return VerdictResult(Verdict.EQUIVALENT, "latex-skeleton")
        for gold in golds:
            result = verify(cand, gold)
            if result.is_equivalent:
                return result
            last = result
            if gold in mapping:
                result = verify(cand, mapping[gold])
                if result.is_equivalent:
                    return result
                if latex_skeleton(cand) and latex_skeleton(cand) == latex_skeleton(mapping[gold]):
                    return VerdictResult(Verdict.EQUIVALENT, "option-skeleton")
                last = result
            if len(gold) >= 2 and gold in cand:
                return VerdictResult(Verdict.EQUIVALENT, "gold-substring")
    for key, val in mapping.items():
        if val and len(val) >= 2 and val in pred and key in {g.upper() for g in golds}:
            return VerdictResult(Verdict.EQUIVALENT, "option-substring")
    return last


def parse_item(row: dict[str, Any]) -> HighSchoolItem | None:
    sol = row.get(GENERATOR_FIELD) or {}
    steps = [str(s).strip() for s in (sol.get("Solution_Steps") or []) if str(s).strip()]
    if not steps:
        return None
    mapping = option_map(row.get("options"))
    golds = gold_answer_candidates(row.get("answer"), mapping)
    pred = extract_pred_answer(steps, mapping)
    verdict = match_answers(pred, golds, mapping)
    qtype = str(row.get("type") or "")
    return HighSchoolItem(
        ques_id=str(row.get("ques_id") or ""),
        problem=format_problem(str(row.get("content") or ""), mapping, qtype),
        steps=steps,
        analysis_steps=analysis_to_steps(str(row.get("analysis") or "")),
        qtype=qtype,
        difficulty=str(row.get("difficulty") or ""),
        gold_answers=golds,
        option_map=mapping,
        extracted_pred=pred,
        answer_verdict=verdict.verdict,
        answer_strategy=verdict.strategy,
        knowledge=list(row.get("knowledge_concepts_list") or []),
    )


def corpus_stats(items: list[HighSchoolItem]) -> dict[str, Any]:
    n = len(items)
    verdicts = Counter(it.answer_verdict for it in items)
    return {
        "n_with_steps": n,
        "answer_verdicts": dict(verdicts),
        "n_answer_correct": sum(1 for it in items if it.answer_correct is True),
        "n_answer_wrong": sum(1 for it in items if it.answer_correct is False),
        "n_answer_unknown": sum(1 for it in items if it.answer_correct is None),
        "difficulty": dict(Counter(it.difficulty for it in items)),
        "qtype": dict(Counter(it.qtype for it in items)),
        "n_steps_mean": (sum(len(it.steps) for it in items) / n) if n else 0.0,
    }


def _to_canonical(
    *,
    sample_id: str,
    problem: str,
    steps: list[str],
    source: str,
    gold_process_correct: bool,
    gold_first_error_step: int | None,
    gold_final_answer_correct: bool | None,
    metadata: dict[str, Any],
) -> CanonicalSample:
    return CanonicalSample(
        sample_id=sample_id,
        problem=problem,
        steps=steps,
        source=source,
        generator=GENERATOR_FIELD,
        gold_process_correct=gold_process_correct,
        gold_first_error_step=gold_first_error_step,
        gold_final_answer_correct=gold_final_answer_correct,
        metadata=metadata,
    )


def qwen_canonical(item: HighSchoolItem, *, track: str) -> CanonicalSample:
    # qwen_right is unlabeled; never mark gold-correct. Filter by source/track
    # before computing M1–M5.
    return _to_canonical(
        sample_id=f"hs-{track}-{item.ques_id}",
        problem=item.problem,
        steps=item.steps,
        source=f"hs_{track}",
        gold_process_correct=False,
        gold_first_error_step=None,
        gold_final_answer_correct=item.answer_correct,
        metadata={
            "track": track,
            "ques_id": item.ques_id,
            "difficulty": item.difficulty,
            "qtype": item.qtype,
            "extracted_pred": item.extracted_pred,
            "gold_answers": item.gold_answers,
            "answer_verdict": item.answer_verdict,
        },
    )


def official_canonical(item: HighSchoolItem) -> CanonicalSample | None:
    if not item.analysis_steps:
        return None
    return _to_canonical(
        sample_id=f"hs-official-{item.ques_id}",
        problem=item.problem,
        steps=item.analysis_steps,
        source="hs_official",
        gold_process_correct=True,
        gold_first_error_step=None,
        gold_final_answer_correct=True,
        metadata={
            "track": "official",
            "ques_id": item.ques_id,
            "difficulty": item.difficulty,
            "qtype": item.qtype,
            "gold_label_note": "textbook analysis; weak gold-correct",
        },
    )


def _stratified(items: list[HighSchoolItem], n: int, seed: int) -> list[HighSchoolItem]:
    if n >= len(items):
        return list(items)
    rng = random.Random(seed)
    buckets: dict[tuple[str, str], list[HighSchoolItem]] = defaultdict(list)
    for it in items:
        buckets[(it.difficulty or "?", it.qtype or "?")].append(it)
    for rows in buckets.values():
        rng.shuffle(rows)
    keys = sorted(buckets)
    quotas = {k: 0 for k in keys}
    i = 0
    while sum(quotas.values()) < n:
        key = keys[i % len(keys)]
        if quotas[key] < len(buckets[key]):
            quotas[key] += 1
        i += 1
        if i > n * len(keys) + 10:
            break
    picked: list[HighSchoolItem] = []
    for key, q in quotas.items():
        picked.extend(buckets[key][:q])
    rng.shuffle(picked)
    return picked[:n]


def build_eval_samples(
    items: list[HighSchoolItem],
    *,
    n_wrong: int,
    n_right: int,
    n_official: int,
    n_adversarial: int,
    seed: int,
) -> list[CanonicalSample]:
    wrong = [it for it in items if it.answer_correct is False]
    right = [it for it in items if it.answer_correct is True]
    with_analysis = [it for it in items if it.analysis_steps]

    samples: list[CanonicalSample] = []
    for it in _stratified(wrong, n_wrong, seed):
        samples.append(qwen_canonical(it, track="qwen_wrong"))
    for it in _stratified(right, n_right, seed + 1):
        samples.append(qwen_canonical(it, track="qwen_right"))

    official_pool_n = max(n_official, n_adversarial * 4)
    official_items = _stratified(with_analysis, official_pool_n, seed + 2)
    official_samples: list[CanonicalSample] = []
    for it in official_items:
        sample = official_canonical(it)
        if sample is not None:
            official_samples.append(sample)
    samples.extend(official_samples[:n_official])

    adv = build_adversarial(official_samples, n=n_adversarial, seed=seed + 3)
    for item in adv:
        sample = item.to_canonical()
        sample.source = "hs_adversarial"
        sample.metadata = {
            **sample.metadata,
            "track": "adversarial",
            "mutation": item.mutation,
            "gold_error_type": item.gold_error_type,
        }
        samples.append(sample)
    return samples


def sample_to_row(sample: CanonicalSample) -> dict[str, Any]:
    return {
        "sample_id": sample.sample_id,
        "problem": sample.problem,
        "steps": sample.steps,
        "source": sample.source,
        "generator": sample.generator,
        "gold_process_correct": sample.gold_process_correct,
        "gold_first_error_step": sample.gold_first_error_step,
        "gold_final_answer_correct": sample.gold_final_answer_correct,
        "metadata": sample.metadata,
    }


def row_to_sample(row: dict[str, Any]) -> CanonicalSample:
    return CanonicalSample(
        sample_id=row["sample_id"],
        problem=row["problem"],
        steps=list(row["steps"]),
        source=row["source"],
        generator=str(row.get("generator") or GENERATOR_FIELD),
        gold_process_correct=bool(row.get("gold_process_correct")),
        gold_first_error_step=row.get("gold_first_error_step"),
        gold_final_answer_correct=row.get("gold_final_answer_correct"),
        metadata=dict(row.get("metadata") or {}),
    )


def dump_eval_jsonl(path: str | Path, samples: list[CanonicalSample]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample_to_row(sample), ensure_ascii=False) + "\n")
    return path


def load_eval_jsonl(path: str | Path) -> list[CanonicalSample]:
    samples: list[CanonicalSample] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(row_to_sample(json.loads(line)))
    return samples


def pb_harmonic_f1(error_acc: float | None, correct_acc: float | None) -> float | None:
    """ProcessBench headline: harmonic mean of error-set acc and correct-set acc."""
    if error_acc is None or correct_acc is None:
        return None
    if error_acc + correct_acc == 0:
        return 0.0
    return 2 * error_acc * correct_acc / (error_acc + correct_acc)
