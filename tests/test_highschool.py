"""Tests for the high-school corpus adapter."""

from __future__ import annotations

from src.benchmark.highschool import (
    analysis_to_steps,
    extract_pred_answer,
    gold_answer_candidates,
    match_answers,
    option_map,
    parse_item,
    pb_harmonic_f1,
    qwen_canonical,
)
from src.verifier.answer_verifier import Verdict


def test_option_map_and_choice_match():
    mapping = option_map(
        [
            {
                "option_id": 0,
                "option_values": [
                    {"key": "A", "value": "3.2"},
                    {"key": "C", "value": "3"},
                ],
            }
        ]
    )
    golds = gold_answer_candidates(["C"], mapping)
    assert "C" in golds
    assert "3" in golds
    hit = match_answers("3", golds, mapping)
    assert hit.verdict == Verdict.EQUIVALENT
    hit_letter = match_answers("C", golds, mapping)
    assert hit_letter.verdict == Verdict.EQUIVALENT


def test_extract_choice_letter_from_last_step():
    pred = extract_pred_answer(["计算得 3", "确定正确选项为 D"], {})
    assert pred == "D"


def test_extract_fill_in_from_equation():
    pred = extract_pred_answer(["解方程得 $\\varLambda=6.4$"], {})
    assert pred is not None
    assert "6.4" in pred


def test_gold_split_on_hash():
    golds = gold_answer_candidates([r"6.4##$$\frac{32}{5}$$"], {})
    assert "6.4" in golds


def test_analysis_prefers_detailed_solution():
    steps = analysis_to_steps("【分析】略。【详解】第一步。第二步。故选：C。")
    assert any("第一步" in s for s in steps)
    assert all("【分析】" not in s for s in steps)


def test_qwen_wrong_is_process_invalid_without_first_error():
    item = parse_item(
        {
            "ques_id": "t1",
            "content": "1+1=?",
            "type": "填空",
            "difficulty": "容易",
            "answer": ["2"],
            "options": {},
            "analysis": "【详解】1+1=2。",
            "knowledge_concepts_list": [],
            "step_by_step_solution_gpt4o": {"Solution_Steps": ["1+1=3", "答案为 3"]},
        }
    )
    assert item is not None
    assert item.answer_correct is False
    sample = qwen_canonical(item, track="qwen_wrong")
    assert sample.gold_process_correct is False
    assert sample.gold_first_error_step is None
    assert sample.gold_final_answer_correct is False


def test_latex_skeleton_matches_sqrt():
    mapping = option_map(
        [{"option_values": [{"key": "A", "value": r"$$2 \sqrt{3}$$"}]}]
    )
    golds = gold_answer_candidates(["A"], mapping)
    hit = match_answers(r"2\sqrt{3}", golds, mapping)
    assert hit.verdict == Verdict.EQUIVALENT


def test_nested_boxed_fraction():
    pred = extract_pred_answer(
        [r"所以实数$a$的值为$\boxed{\frac{2}{11}}$。"],
        {},
    )
    assert pred is not None
    assert "2" in pred and "11" in pred


def test_pb_f1_is_harmonic_mean():
    assert abs(pb_harmonic_f1(0.5, 1.0) - 2 / 3) < 1e-9
    assert pb_harmonic_f1(None, 1.0) is None
