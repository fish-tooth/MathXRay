"""Tests for the solve → verify → audit pipeline with a mock provider."""

from __future__ import annotations

import json

from src.evaluator.direct_judge import DirectJudge
from src.evaluator.hybrid import HybridEvaluator
from src.llm.mock_provider import MockProvider
from src.pipeline import MathXRayPipeline
from src.solver.math_solver import MathSolver

SOLVE = json.dumps(
    {
        "problem": "2+2",
        "solution_steps": [
            {
                "step_id": 1,
                "statement": "Add the numbers.",
                "expression": "2+2=4",
                "depends_on": [],
            }
        ],
        "final_answer": "4",
    }
)
JUDGE = json.dumps(
    {
        "process_correct": True,
        "first_error_step": None,
        "error_type": None,
        "reason": "ok",
    }
)


def test_pipeline_supported_correct():
    solver = MathSolver(MockProvider([SOLVE]), "solve")
    judge = DirectJudge(MockProvider([JUDGE]), "judge", model="mock")
    pipe = MathXRayPipeline(solver, HybridEvaluator(judge))
    result = pipe.run("What is 2+2?", gold_answer="4", sample_id="t1")
    assert result.solver.ok
    assert result.answer is not None and result.answer.is_equivalent
    assert result.audit is not None and result.audit.process_correct is True
    assert result.unsupported_answer is False


def test_pipeline_unsupported_when_process_invalid():
    bad = json.dumps(
        {
            "problem": "2+2",
            "solution_steps": [
                {
                    "step_id": 1,
                    "statement": "wrong arithmetic",
                    "expression": "2+2=5",
                    "depends_on": [],
                },
                {
                    "step_id": 2,
                    "statement": "but we still say 4",
                    "expression": "final=4",
                    "depends_on": [1],
                },
            ],
            "final_answer": "4",
        }
    )
    solver = MathSolver(MockProvider([bad]), "solve")
    judge = DirectJudge(
        MockProvider(
            [
                json.dumps(
                    {
                        "process_correct": True,
                        "first_error_step": None,
                        "reason": "missed it",
                    }
                )
            ]
        ),
        "judge",
        model="mock",
    )
    pipe = MathXRayPipeline(solver, HybridEvaluator(judge))
    result = pipe.run("What is 2+2?", gold_answer="4")
    assert result.answer is not None and result.answer.is_equivalent
    assert result.audit is not None and result.audit.process_correct is False
    assert result.audit.first_error_step == 1
    assert result.unsupported_answer is True
