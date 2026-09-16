"""Tests for stepwise parse and the reflective critic loop."""

from __future__ import annotations

from src.benchmark.processbench_adapter import CanonicalSample
from src.evaluator.reflective import ReflectiveCritic
from src.evaluator.stepwise import parse_stepwise_raw
from src.llm.mock_provider import MockProvider

PROMPTS = {
    "independent_solve": "solve",
    "stepwise_critic": "stepwise",
    "accuser": "accuser",
    "defender": "defender",
    "arbiter": "arbiter",
}


def _sample(**kw) -> CanonicalSample:
    base = dict(
        sample_id="hs-1",
        problem="写出一个与 AB 共线的向量坐标",
        steps=[
            "AB=(3,-4)",
            "共线向量可写成 λAB",
            "所以所求为 (3λ,-4λ)",
        ],
        source="hs_qwen_wrong",
        gold_process_correct=False,
        gold_final_answer_correct=False,
        metadata={"extracted_pred": "(3λ,-4λ)", "track": "qwen_wrong"},
    )
    base.update(kw)
    return CanonicalSample(**base)


def test_stepwise_earliest_invalid_wins():
    raw = """{
      "steps": [
        {"step_id": 1, "verdict": "VALID", "claim": "ok", "error_type": null},
        {"step_id": 2, "verdict": "INVALID", "claim": "2+2=5", "error_type": "ARITHMETIC_ERROR"},
        {"step_id": 3, "verdict": "INVALID", "claim": "inherits", "error_type": "ARITHMETIC_ERROR"}
      ],
      "reason": "step 2"
    }"""
    parsed = parse_stepwise_raw(raw, n_steps=3)
    assert parsed.status == "SUCCESS"
    assert parsed.process_correct is False
    assert parsed.first_error_step == 2
    assert parsed.error_type == "ARITHMETIC_ERROR"


def test_stepwise_explicit_unknown_is_inconclusive():
    raw = """{
      "steps": [
        {"step_id": 1, "verdict": "VALID", "claim": "ok", "error_type": null},
        {"step_id": 2, "verdict": "UNKNOWN", "claim": "unclear", "error_type": null}
      ],
      "reason": "not sure"
    }"""
    parsed = parse_stepwise_raw(raw, n_steps=2)
    assert parsed.process_correct is None
    assert parsed.unknown_steps == [2]


def test_stepwise_boxed_minus_one():
    parsed = parse_stepwise_raw(r"the solution is fine \boxed{-1}", n_steps=2)
    assert parsed.status == "SUCCESS"
    assert parsed.process_correct is True


def test_answer_mismatch_forces_accuser_completeness():
    independent = '{"final_answer": "(3,-4)", "outline": ["take λ=1"]}'
    stepwise = """{"steps": [
        {"step_id": 1, "verdict": "VALID", "claim": "AB", "error_type": null},
        {"step_id": 2, "verdict": "VALID", "claim": "family", "error_type": null},
        {"step_id": 3, "verdict": "VALID", "claim": "parametric", "error_type": null}
      ], "reason": "algebra ok"}"""
    accuser = """{"charge_stands": true, "first_error_step": 3,
        "error_type": "ANSWER_FORMAT_ERROR",
        "charge": "problem asks for one vector",
        "counterexample": "λ=1 gives (3,-4), λ=2 gives (6,-8)"}"""
    defender = '{"rebuts": false, "reason": "the last step leaves a free parameter"}'
    critic = ReflectiveCritic(
        MockProvider([independent, stepwise, accuser, defender]),
        PROMPTS,
        answer_aware=True,
    )
    pred = critic.judge(_sample())
    assert pred.parse_status == "SUCCESS"
    assert pred.process_correct is False
    assert pred.first_error_step == 3
    assert pred.error_type == "ANSWER_FORMAT_ERROR"
    assert pred.extra["debate_triggered"] is True
    assert "answer_mismatch" in pred.extra["triggers"]
    assert critic._provider.call_count == 4


def test_mismatch_gate_overrides_lenient_stepwise():
    independent = '{"final_answer": "(3,-4)", "outline": ["λ=1"]}'
    stepwise = """{"steps": [
        {"step_id": 1, "verdict": "VALID", "claim": "ok", "error_type": null}
      ], "reason": "all valid"}"""
    accuser = '{"charge_stands": false, "first_error_step": null, "error_type": null, "charge": "", "counterexample": ""}'
    critic = ReflectiveCritic(
        MockProvider([independent, stepwise, accuser]),
        PROMPTS,
        answer_aware=True,
    )
    pred = critic.judge(_sample())
    assert pred.process_correct is False
    assert pred.error_type == "ANSWER_FORMAT_ERROR"


def test_no_debate_when_process_valid_and_answers_agree():
    independent = '{"final_answer": "2", "outline": ["1+1"]}'
    stepwise = """{"steps": [
        {"step_id": 1, "verdict": "VALID", "claim": "ok", "error_type": null},
        {"step_id": 2, "verdict": "VALID", "claim": "ok", "error_type": null}
      ], "reason": "ok"}"""
    critic = ReflectiveCritic(
        MockProvider([independent, stepwise, '{"should":"not be called"}']),
        PROMPTS,
        answer_aware=True,
    )
    sample = _sample(
        problem="1+1=?",
        steps=["1+1=2", "answer 2"],
        gold_final_answer_correct=True,
        gold_process_correct=True,
        metadata={"extracted_pred": "2"},
    )
    pred = critic.judge(sample)
    assert pred.process_correct is True
    assert pred.extra["debate_triggered"] is False
    assert critic._provider.call_count == 2
