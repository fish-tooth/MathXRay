"""End-to-end solve → answer-verify → process-audit pipeline (R1 / R4 / R2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.evaluator.hybrid import HybridEvaluator, ProcessAudit
from src.solver.math_solver import MathSolver, SolverResult
from src.verifier.answer_verifier import VerdictResult, verify


@dataclass
class PipelineResult:
    problem: str
    solver: SolverResult
    answer: VerdictResult | None
    audit: ProcessAudit | None
    unsupported_answer: bool = False
    gold_answer: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "problem": self.problem,
            "solver": self.solver.to_dict(),
            "answer": None
            if self.answer is None
            else {
                "verdict": self.answer.verdict,
                "strategy": self.answer.strategy,
                "evidence": self.answer.evidence,
            },
            "audit": None if self.audit is None else self.audit.to_dict(),
            "unsupported_answer": self.unsupported_answer,
            "gold_answer": self.gold_answer,
        }


class MathXRayPipeline:
    def __init__(self, solver: MathSolver, evaluator: HybridEvaluator) -> None:
        self.solver = solver
        self.evaluator = evaluator

    def run(
        self,
        problem: str,
        *,
        gold_answer: str | None = None,
        sample_id: str = "live",
        gen_cfg: dict[str, Any] | None = None,
    ) -> PipelineResult:
        gen_cfg = gen_cfg or {}
        solved = self.solver.solve(problem, **gen_cfg)
        answer: VerdictResult | None = None
        if gold_answer is not None and solved.solution is not None:
            answer = verify(solved.solution.final_answer, gold_answer)

        audit: ProcessAudit | None = None
        if solved.solution is not None:
            steps = [
                " ".join(
                    p
                    for p in (
                        s.statement,
                        f"({s.expression})" if s.expression else "",
                    )
                    if p
                ).strip()
                for s in solved.solution.solution_steps
            ]
            expressions = [s.expression for s in solved.solution.solution_steps]
            depends = {
                s.step_id: list(s.depends_on) for s in solved.solution.solution_steps
            }
            audit = self.evaluator.audit_texts(
                steps,
                sample_id=sample_id,
                expressions=expressions,
                depends_on=depends,
                problem=problem,
                source="app",
            )

        unsupported = False
        if answer is not None and answer.is_equivalent and audit is not None:
            unsupported = audit.process_correct is False

        return PipelineResult(
            problem=problem,
            solver=solved,
            answer=answer,
            audit=audit,
            unsupported_answer=unsupported,
            gold_answer=gold_answer,
        )
