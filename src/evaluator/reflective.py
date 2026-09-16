"""Reflective critic: independent solve + stepwise critique + optional debate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.benchmark.highschool import extract_pred_answer
from src.benchmark.processbench_adapter import CanonicalSample
from src.evaluator.direct_judge import JudgePrediction, extract_json_object
from src.evaluator.stepwise import StepwiseResult, build_stepwise_messages, parse_stepwise_raw
from src.evaluator.symbolic import first_symbolic_invalid, verify_step
from src.llm.base import BaseLLMProvider
from src.llm.hy3_provider import is_non_retryable
from src.taxonomy import normalize_error_type
from src.verifier.answer_verifier import verify


@dataclass
class IndependentSolve:
    status: str
    final_answer: str | None = None
    outline: list[str] = field(default_factory=list)
    raw: str = ""
    error: str | None = None


@dataclass
class Charge:
    charge_stands: bool
    first_error_step: int | None = None
    error_type: str | None = None
    charge: str = ""
    counterexample: str = ""
    raw: str = ""
    error: str | None = None


@dataclass
class Defense:
    rebuts: bool | None = None
    reason: str = ""
    raw: str = ""
    error: str | None = None


class ReflectiveCritic:
    """Four-pass critic. Independent solve is a private scaffold, not gold."""

    name = "R1-ReflectiveCritic"

    def __init__(
        self,
        provider: BaseLLMProvider,
        prompts: dict[str, str],
        *,
        model: str = "",
        answer_aware: bool = False,
    ) -> None:
        self._provider = provider
        self._prompts = prompts
        self._model = model
        self.answer_aware = answer_aware
        self.quota_exhausted = False

    def _complete(self, messages: list[dict[str, str]], **gen_cfg: Any):
        result = self._provider.complete(messages, **gen_cfg)
        if result.error and is_non_retryable(result.error):
            self.quota_exhausted = True
        return result

    def judge(self, sample: CanonicalSample, **gen_cfg: Any) -> JudgePrediction:
        calls = 0
        extra: dict[str, Any] = {"method": self.name, "debate_triggered": False, "triggers": []}

        independent = self._independent_solve(sample.problem, **gen_cfg)
        calls += 1
        extra["independent"] = {
            "status": independent.status,
            "final_answer": independent.final_answer,
            "outline": independent.outline,
            "error": independent.error,
        }
        if self.quota_exhausted:
            return self._fail(sample, "quota exhausted", calls, extra)

        stepwise_raw = self._complete(
            build_stepwise_messages(sample.problem, sample.steps, self._prompts["stepwise_critic"]),
            **gen_cfg,
        )
        calls += 1
        extra["stepwise_error"] = stepwise_raw.error
        stepwise = parse_stepwise_raw(stepwise_raw.raw or "", len(sample.steps))
        extra["stepwise"] = stepwise.to_dict()
        if self.quota_exhausted:
            return self._fail(sample, stepwise_raw.error or "quota exhausted", calls, extra)

        student_answer = _student_answer(sample)
        extra["student_answer"] = student_answer
        independent_disagree = _answers_disagree(independent.final_answer, student_answer)
        answer_mismatch = bool(
            self.answer_aware and sample.gold_final_answer_correct is False
        )
        extra["independent_disagree"] = independent_disagree
        extra["answer_mismatch"] = answer_mismatch

        symbolic_rows = [verify_step(i, text) for i, text in enumerate(sample.steps, start=1)]
        sym_first = first_symbolic_invalid(symbolic_rows)
        extra["symbolic_first_invalid"] = sym_first

        triggers: list[str] = []
        if answer_mismatch:
            triggers.append("answer_mismatch")
        if independent_disagree:
            triggers.append("independent_disagree")
        if stepwise.status != "SUCCESS" or stepwise.process_correct is None or stepwise.unknown_steps:
            triggers.append("stepwise_unknown")
        extra["triggers"] = triggers

        debate = None
        # Symbolic INVALID is enough unless we still need a completeness check.
        skip_debate = sym_first is not None and not answer_mismatch and not independent_disagree
        if triggers and not skip_debate:
            extra["debate_triggered"] = True
            debate = self._debate(sample, independent, student_answer, stepwise, triggers, **gen_cfg)
            calls += debate.get("n_calls", 0)
            extra["debate"] = debate
            if self.quota_exhausted:
                fused = _fuse(
                    stepwise,
                    debate,
                    sym_first,
                    answer_mismatch=answer_mismatch,
                    n_steps=len(sample.steps),
                )
                return _prediction(sample, fused, stepwise, calls, extra, error=debate.get("error"))

        fused = _fuse(
            stepwise,
            debate,
            sym_first,
            answer_mismatch=answer_mismatch,
            n_steps=len(sample.steps),
        )
        extra["n_calls"] = calls
        return JudgePrediction(
            sample_id=sample.sample_id,
            process_correct=fused["process_correct"],
            first_error_step=fused["first_error_step"],
            error_type=fused["error_type"],
            reason=fused["reason"],
            raw=stepwise.raw,
            reasoning="",
            parse_status="SUCCESS" if fused["process_correct"] is not None else "FAILURE",
            parse_error=fused.get("error"),
            error=None if fused["process_correct"] is not None else fused.get("error"),
            model=self._model,
            retry_count=calls,
            extra=extra,
        )

    def _fail(self, sample: CanonicalSample, error: str, calls: int, extra: dict[str, Any]) -> JudgePrediction:
        extra["n_calls"] = calls
        return JudgePrediction(
            sample_id=sample.sample_id,
            parse_status="FAILURE",
            parse_error=error,
            error=error,
            model=self._model,
            retry_count=calls,
            extra=extra,
        )

    def _independent_solve(self, problem: str, **gen_cfg: Any) -> IndependentSolve:
        messages = [
            {"role": "system", "content": self._prompts["independent_solve"]},
            {"role": "user", "content": f"Problem:\n{problem}"},
        ]
        result = self._complete(messages, **gen_cfg)
        if not result.ok:
            return IndependentSolve(status="FAILURE", error=result.error, raw=result.raw or "")
        try:
            data = extract_json_object(result.raw or "")
        except ValueError as exc:
            return IndependentSolve(status="FAILURE", error=str(exc), raw=result.raw or "")
        if not isinstance(data, dict):
            return IndependentSolve(status="FAILURE", error="not an object", raw=result.raw or "")
        answer = data.get("final_answer")
        outline = data.get("outline") if isinstance(data.get("outline"), list) else []
        return IndependentSolve(
            status="SUCCESS",
            final_answer=str(answer).strip() if answer not in (None, "") else None,
            outline=[str(x) for x in outline],
            raw=result.raw or "",
        )

    def _debate(
        self,
        sample: CanonicalSample,
        independent: IndependentSolve,
        student_answer: str | None,
        stepwise: StepwiseResult,
        triggers: list[str],
        **gen_cfg: Any,
    ) -> dict[str, Any]:
        n_calls = 0
        payload: dict[str, Any] = {"n_calls": 0}
        accuser_user = _accuser_user(sample, independent, student_answer, stepwise, triggers)
        acc_res = self._complete(
            [
                {"role": "system", "content": self._prompts["accuser"]},
                {"role": "user", "content": accuser_user},
            ],
            **gen_cfg,
        )
        n_calls += 1
        charge = parse_charge(acc_res.raw or "", n_steps=len(sample.steps))
        if acc_res.error:
            charge.error = acc_res.error
        payload["accuser"] = {
            "charge_stands": charge.charge_stands,
            "first_error_step": charge.first_error_step,
            "error_type": charge.error_type,
            "charge": charge.charge,
            "counterexample": charge.counterexample,
            "error": charge.error or acc_res.error,
        }
        if self.quota_exhausted or not charge.charge_stands or charge.error:
            payload["n_calls"] = n_calls
            payload["error"] = acc_res.error
            return payload

        def_res = self._complete(
            [
                {"role": "system", "content": self._prompts["defender"]},
                {"role": "user", "content": _defender_user(sample, charge)},
            ],
            **gen_cfg,
        )
        n_calls += 1
        defense = parse_defense(def_res.raw or "")
        payload["defender"] = {
            "rebuts": defense.rebuts,
            "reason": defense.reason,
            "error": defense.error or def_res.error,
        }
        if self.quota_exhausted:
            payload["n_calls"] = n_calls
            payload["error"] = def_res.error
            return payload

        if defense.rebuts is True:
            arb_res = self._complete(
                [
                    {"role": "system", "content": self._prompts["arbiter"]},
                    {"role": "user", "content": _arbiter_user(sample, stepwise, charge, defense)},
                ],
                **gen_cfg,
            )
            n_calls += 1
            payload["arbiter"] = parse_arbiter(arb_res.raw or "")
            payload["arbiter"]["error"] = arb_res.error
        payload["n_calls"] = n_calls
        return payload


def _student_answer(sample: CanonicalSample) -> str | None:
    meta = sample.metadata or {}
    if meta.get("extracted_pred"):
        return str(meta["extracted_pred"])
    mapping = meta.get("option_map") if isinstance(meta.get("option_map"), dict) else {}
    return extract_pred_answer(sample.steps, mapping)


def _answers_disagree(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    result = verify(a, b)
    if result.is_equivalent:
        return False
    # UNKNOWN is not treated as disagreement; only a clear mismatch.
    from src.verifier.answer_verifier import Verdict

    return result.verdict == Verdict.NOT_EQUIVALENT


def _accuser_user(
    sample: CanonicalSample,
    independent: IndependentSolve,
    student_answer: str | None,
    stepwise: StepwiseResult,
    triggers: list[str],
) -> str:
    lines = [
        f"Problem:\n{sample.problem}",
        "",
        "Student steps:",
    ]
    for i, step in enumerate(sample.steps, start=1):
        lines.append(f"Step {i}: {step}")
    lines.append("")
    lines.append(f"Triggers: {', '.join(triggers)}")
    if student_answer:
        lines.append(f"Extracted student answer: {student_answer}")
    if independent.final_answer:
        lines.append(
            f"Private independent outline answer (not gold): {independent.final_answer}"
        )
    if stepwise.unknown_steps:
        lines.append(f"UNKNOWN steps from first pass: {stepwise.unknown_steps}")
    if "answer_mismatch" in triggers:
        lines.append(
            "Automatic verification says the student answer does not match the "
            "required official answer. You are not given that official answer."
        )
    return "\n".join(lines)


def _defender_user(sample: CanonicalSample, charge: Charge) -> str:
    lines = [f"Problem:\n{sample.problem}", "", "Student steps:"]
    for i, step in enumerate(sample.steps, start=1):
        lines.append(f"Step {i}: {step}")
    lines.append("")
    lines.append("Accuser charge:")
    lines.append(f"step={charge.first_error_step} type={charge.error_type}")
    lines.append(charge.charge)
    if charge.counterexample:
        lines.append(f"Counterexample: {charge.counterexample}")
    return "\n".join(lines)


def _arbiter_user(
    sample: CanonicalSample,
    stepwise: StepwiseResult,
    charge: Charge,
    defense: Defense,
) -> str:
    return (
        f"Problem:\n{sample.problem}\n\n"
        f"Stepwise: process_correct={stepwise.process_correct} "
        f"first_error={stepwise.first_error_step} unknown={stepwise.unknown_steps}\n"
        f"Accuser: stands={charge.charge_stands} step={charge.first_error_step} "
        f"type={charge.error_type} charge={charge.charge} "
        f"counterexample={charge.counterexample}\n"
        f"Defender: rebuts={defense.rebuts} reason={defense.reason}\n"
        f"n_steps={len(sample.steps)}"
    )


def parse_charge(raw: str, *, n_steps: int) -> Charge:
    if not raw.strip():
        return Charge(charge_stands=False, error="empty response", raw=raw)
    try:
        data = extract_json_object(raw)
    except ValueError as exc:
        return Charge(charge_stands=False, error=str(exc), raw=raw)
    if not isinstance(data, dict):
        return Charge(charge_stands=False, error="not an object", raw=raw)
    stands = bool(data.get("charge_stands"))
    fes = data.get("first_error_step")
    step: int | None = fes if isinstance(fes, int) and 1 <= fes <= n_steps else None
    return Charge(
        charge_stands=stands,
        first_error_step=step,
        error_type=normalize_error_type(data.get("error_type")) if stands else None,
        charge=str(data.get("charge") or ""),
        counterexample=str(data.get("counterexample") or ""),
        raw=raw,
    )


def parse_defense(raw: str) -> Defense:
    if not raw.strip():
        return Defense(rebuts=None, error="empty response", raw=raw)
    try:
        data = extract_json_object(raw)
    except ValueError as exc:
        return Defense(rebuts=None, error=str(exc), raw=raw)
    if not isinstance(data, dict) or not isinstance(data.get("rebuts"), bool):
        return Defense(rebuts=None, error="invalid defense JSON", raw=raw)
    return Defense(rebuts=bool(data["rebuts"]), reason=str(data.get("reason") or ""), raw=raw)


def parse_arbiter(raw: str) -> dict[str, Any]:
    if not raw.strip():
        return {"status": "FAILURE", "error": "empty response"}
    try:
        data = extract_json_object(raw)
    except ValueError as exc:
        return {"status": "FAILURE", "error": str(exc)}
    if not isinstance(data, dict) or not isinstance(data.get("process_correct"), bool):
        return {"status": "FAILURE", "error": "invalid arbiter JSON"}
    fes = data.get("first_error_step")
    if data["process_correct"] is True:
        fes = None
    elif not isinstance(fes, int) or fes < 1:
        return {"status": "FAILURE", "error": "arbiter missing first_error_step"}
    return {
        "status": "SUCCESS",
        "process_correct": data["process_correct"],
        "first_error_step": fes,
        "error_type": normalize_error_type(data.get("error_type"))
        if data["process_correct"] is False
        else None,
        "reason": str(data.get("reason") or ""),
    }


def _fuse(
    stepwise: StepwiseResult,
    debate: dict[str, Any] | None,
    sym_first: int | None,
    *,
    answer_mismatch: bool,
    n_steps: int,
) -> dict[str, Any]:
    """Deterministic fusion. Symbolic INVALID wins; mismatch forbids VALID."""
    if sym_first is not None:
        err = stepwise.error_type if stepwise.first_error_step == sym_first else "ARITHMETIC_ERROR"
        return {
            "process_correct": False,
            "first_error_step": sym_first,
            "error_type": err or "ARITHMETIC_ERROR",
            "reason": f"symbolic INVALID at step {sym_first}",
        }

    arbiter = (debate or {}).get("arbiter") or {}
    if arbiter.get("status") == "SUCCESS":
        out = {
            "process_correct": arbiter["process_correct"],
            "first_error_step": arbiter.get("first_error_step"),
            "error_type": arbiter.get("error_type"),
            "reason": arbiter.get("reason") or "arbiter",
        }
        return _apply_mismatch_gate(out, answer_mismatch, n_steps, debate)

    accuser = (debate or {}).get("accuser") or {}
    defender = (debate or {}).get("defender") or {}
    if accuser.get("charge_stands") and defender.get("rebuts") is not True:
        out = {
            "process_correct": False,
            "first_error_step": accuser.get("first_error_step"),
            "error_type": accuser.get("error_type") or "OTHER",
            "reason": accuser.get("charge") or "accuser charge stands",
        }
        return _apply_mismatch_gate(out, answer_mismatch, n_steps, debate)

    if stepwise.status == "SUCCESS" and stepwise.process_correct is True:
        out = {
            "process_correct": True,
            "first_error_step": None,
            "error_type": None,
            "reason": stepwise.reason or "stepwise all VALID",
        }
        return _apply_mismatch_gate(out, answer_mismatch, n_steps, debate)

    if stepwise.status == "SUCCESS" and stepwise.process_correct is False:
        out = {
            "process_correct": False,
            "first_error_step": stepwise.first_error_step,
            "error_type": stepwise.error_type or "OTHER",
            "reason": stepwise.reason or "stepwise INVALID",
        }
        return _apply_mismatch_gate(out, answer_mismatch, n_steps, debate)

    if answer_mismatch:
        return {
            "process_correct": False,
            "first_error_step": (accuser or {}).get("first_error_step") or n_steps,
            "error_type": (accuser or {}).get("error_type") or "ANSWER_FORMAT_ERROR",
            "reason": "answer mismatch with no conceded valid process",
        }

    return {
        "process_correct": None,
        "first_error_step": None,
        "error_type": None,
        "reason": stepwise.error or "inconclusive",
        "error": stepwise.error or "inconclusive",
    }


def _apply_mismatch_gate(
    out: dict[str, Any],
    answer_mismatch: bool,
    n_steps: int,
    debate: dict[str, Any] | None,
) -> dict[str, Any]:
    if answer_mismatch and out.get("process_correct") is True:
        accuser = (debate or {}).get("accuser") or {}
        out["process_correct"] = False
        out["first_error_step"] = accuser.get("first_error_step") or n_steps
        out["error_type"] = accuser.get("error_type") or "ANSWER_FORMAT_ERROR"
        out["reason"] = (
            (out.get("reason") or "") + "; overridden: student answer failed verification"
        ).strip("; ")
    return out


def _prediction(
    sample: CanonicalSample,
    fused: dict[str, Any],
    stepwise: StepwiseResult,
    calls: int,
    extra: dict[str, Any],
    error: str | None = None,
) -> JudgePrediction:
    extra["n_calls"] = calls
    ok = fused.get("process_correct") is not None
    return JudgePrediction(
        sample_id=sample.sample_id,
        process_correct=fused.get("process_correct"),
        first_error_step=fused.get("first_error_step"),
        error_type=fused.get("error_type"),
        reason=str(fused.get("reason") or ""),
        raw=stepwise.raw,
        parse_status="SUCCESS" if ok else "FAILURE",
        parse_error=None if ok else (error or fused.get("error")),
        error=None if ok else (error or fused.get("error")),
        retry_count=calls,
        extra=extra,
    )
