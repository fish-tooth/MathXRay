"""Tests for adversarial mutations and SolveBench parsers."""

from __future__ import annotations

from src.benchmark.adversarial import build_adversarial, mutate_arithmetic, mutate_unused_claim
from src.benchmark.processbench_adapter import CanonicalSample
from src.benchmark.solvebench import extract_boxed, extract_gsm8k_answer, math_level_to_difficulty


def _correct(**kw) -> CanonicalSample:
    base = dict(
        sample_id="x-1",
        problem="p",
        steps=["Start with 10", "Then 10 + 2 = 12", "So the answer is 12"],
        source="gsm8k",
        gold_process_correct=True,
        gold_final_answer_correct=True,
    )
    base.update(kw)
    return CanonicalSample(**base)


def test_arithmetic_changes_a_number():
    out = mutate_arithmetic("Then 10 + 2 = 12")
    assert out is not None
    assert out != "Then 10 + 2 = 12"


def test_unused_claim_is_answer_preserving():
    items = build_adversarial(
        [_correct(sample_id=f"c{i}") for i in range(8)],
        n=4,
        seed=0,
        mutations=("unused_claim",),
    )
    assert items
    assert all(it.answer_preserving for it in items)
    assert all(it.gold_first_error_step is not None for it in items)
    assert all("2 + 2 = 5" in it.steps[it.mutation_step - 1] for it in items)


def test_gold_first_error_matches_mutation_step():
    items = build_adversarial([_correct()], n=1, seed=1, mutations=("arithmetic",))
    assert items
    assert items[0].gold_process_correct is False
    assert 1 <= items[0].gold_first_error_step <= 3


def test_extract_gsm8k():
    assert extract_gsm8k_answer("blah #### 42") == "42"


def test_extract_boxed_nested():
    assert extract_boxed(r"thus \boxed{\frac{1}{2}}") == r"\frac{1}{2}"


def test_math_level_mapping_frozen():
    assert math_level_to_difficulty(1) == "D2"
    assert math_level_to_difficulty(3) == "D3"
    assert math_level_to_difficulty(5) == "D4"
