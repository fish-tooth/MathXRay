"""Precision-first symbolic / arithmetic step verifier (M8 / R6).

A step is ``INVALID`` only when a parseable equality is demonstrably false.
Unparseable or out-of-scope claims return ``UNKNOWN`` and never block the pipeline.
"""

from __future__ import annotations

import re
import warnings
from dataclasses import dataclass

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from src.verifier.answer_verifier import Verdict, verify

VALID = "VALID"
INVALID = "INVALID"
UNKNOWN = "UNKNOWN"

_TRANSFORMATIONS = standard_transformations + (
    convert_xor,
    implicit_multiplication_application,
)

_EQ_SPLIT = re.compile(r"(==|=)")
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
_UNSAFE_EXPR = re.compile(
    r"\b(set|lambda|eval|exec|__import__)\b|[{}\[\]\\]|:"
)


@dataclass
class StepSymbolicResult:
    step_id: int
    verdict: str
    evidence: str = ""
    expression: str | None = None

    @property
    def is_invalid(self) -> bool:
        return self.verdict == INVALID


def _to_sympy(text: str) -> sp.Expr | None:
    if not text or len(text) > 80:
        return None
    lowered = text.lower()
    if _UNSAFE_EXPR.search(lowered) or "set(" in lowered:
        return None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return parse_expr(text, transformations=_TRANSFORMATIONS, evaluate=True)
    except Exception:
        return None


def _clean_side(text: str) -> str:
    s = text.strip()
    s = s.replace("$$", "").replace("$", "")
    s = s.replace(r"\(", "").replace(r"\)", "")
    s = s.replace(r"\[", "").replace(r"\]", "")
    s = s.replace("×", "*").replace("÷", "/").replace("−", "-")
    s = re.sub(r"\\times", "*", s)
    s = re.sub(r"\\cdot", "*", s)
    s = re.sub(r"\\div", "/", s)
    s = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"(\1)/(\2)", s)
    s = re.sub(r"\\sqrt\{([^{}]+)\}", r"sqrt(\1)", s)
    # Drop leading prose ("Compute 2+2" -> "2+2"). Keep single-letter variables.
    s = re.sub(r"^(?:[A-Za-z]{2,}[\s,:]*)+", "", s).strip()
    s = re.sub(r"\s+", "", s)
    return s


def _extract_equalities(text: str) -> list[tuple[str, str]]:
    """Return (lhs, rhs) pairs from a step. Ignores lone assignment words."""
    found: list[tuple[str, str]] = []
    # Prefer explicit math-like equalities, including chained a = b = c.
    for raw_line in re.split(r"[\n;]", text):
        line = raw_line.strip()
        if "=" not in line:
            continue
        parts = [p.strip() for p in line.split("=") if p.strip()]
        if len(parts) < 2:
            continue
        for i in range(len(parts) - 1):
            lhs, rhs = _clean_side(parts[i]), _clean_side(parts[i + 1])
            if not lhs or not rhs:
                continue
            if len(lhs) > 80 or len(rhs) > 80:
                continue
            found.append((lhs, rhs))
    return found


def verify_equality(lhs: str, rhs: str) -> StepSymbolicResult:
    """Verify a single equality with the same precision-first policy as the answer verifier."""
    expr = f"{lhs}={rhs}"
    if len(lhs) > 60 or len(rhs) > 60:
        return StepSymbolicResult(0, UNKNOWN, "equality too long", expr)
    if _UNSAFE_EXPR.search(lhs.lower()) or _UNSAFE_EXPR.search(rhs.lower()):
        return StepSymbolicResult(0, UNKNOWN, "unsafe equality", expr)
    if not re.fullmatch(r"[0-9A-Za-z_+\-*/^().]+", lhs + rhs):
        return StepSymbolicResult(0, UNKNOWN, "non-algebraic equality", expr)
    if len(re.findall(r"[+\-*/^]", lhs + rhs)) > 16:
        return StepSymbolicResult(0, UNKNOWN, "too many operators", expr)

    if re.fullmatch(r"-?\d+(?:\.\d+)?(?:/\d+)?%?", lhs) and re.fullmatch(
        r"-?\d+(?:\.\d+)?(?:/\d+)?%?", rhs
    ):
        numeric = verify(lhs, rhs)
        if numeric.verdict == Verdict.EQUIVALENT:
            return StepSymbolicResult(0, VALID, "numeric/exact equality", expr)
        if numeric.verdict == Verdict.NOT_EQUIVALENT:
            return StepSymbolicResult(
                0, INVALID, numeric.evidence or "numeric inequality", expr
            )

    left = _to_sympy(lhs)
    right = _to_sympy(rhs)
    if left is None or right is None:
        return StepSymbolicResult(0, UNKNOWN, "unparseable equality", expr)
    try:
        diff = sp.expand(left - right)
    except Exception:
        return StepSymbolicResult(0, UNKNOWN, "symbolic expand failed", expr)
    if diff == 0:
        return StepSymbolicResult(0, VALID, "sympy identity", expr)
    if diff.is_Number:
        return StepSymbolicResult(0, INVALID, f"symbolic difference = {diff}", expr)
    return StepSymbolicResult(0, UNKNOWN, "non-constant symbolic difference", expr)


def verify_step(step_id: int, text: str, expression: str | None = None) -> StepSymbolicResult:
    """Verify one auditable step. UNKNOWN if nothing can be checked safely."""
    if text and len(text) > 240:
        return StepSymbolicResult(step_id, UNKNOWN, "step too long for symbolic check")
    chunks = [t for t in (expression, text) if t]
    equalities: list[tuple[str, str]] = []
    for chunk in chunks:
        equalities.extend(_extract_equalities(chunk))

    if not equalities:
        return StepSymbolicResult(step_id, UNKNOWN, "no parseable equality")

    first_unknown: StepSymbolicResult | None = None
    for lhs, rhs in equalities:
        result = verify_equality(lhs, rhs)
        result.step_id = step_id
        if result.verdict == INVALID:
            return result
        if result.verdict == UNKNOWN and first_unknown is None:
            first_unknown = result
        if result.verdict == VALID:
            # Keep looking: a later explicit false equality still invalidates the step.
            continue
    if first_unknown is not None and all(
        verify_equality(lhs, rhs).verdict != VALID for lhs, rhs in equalities
    ):
        first_unknown.step_id = step_id
        return first_unknown
    return StepSymbolicResult(step_id, VALID, "all parseable equalities hold")


def verify_steps(steps: list[str]) -> list[StepSymbolicResult]:
    return [verify_step(i, step) for i, step in enumerate(steps, start=1)]


def first_symbolic_invalid(results: list[StepSymbolicResult]) -> int | None:
    for item in results:
        if item.is_invalid:
            return item.step_id
    return None
