"""Unit tests for the symbolic step verifier."""

from __future__ import annotations

from src.evaluator.symbolic import INVALID, UNKNOWN, VALID, verify_equality, verify_step, verify_steps


def test_valid_arithmetic_equality():
    r = verify_step(1, "Compute 2+2=4")
    assert r.verdict == VALID


def test_invalid_arithmetic_equality():
    r = verify_step(1, "Compute 2+2=5")
    assert r.verdict == INVALID
    assert r.step_id == 1


def test_unknown_without_equality():
    r = verify_step(1, "By AM-GM the product is maximized.")
    assert r.verdict == UNKNOWN


def test_expression_field_used():
    r = verify_step(2, "the next line", expression="3*4=12")
    assert r.verdict == VALID


def test_fraction_percentage_via_verifier():
    r = verify_equality("1/2", "0.5")
    assert r.verdict == VALID


def test_first_invalid_in_trace():
    rows = verify_steps(["1+1=2", "2+2=5", "5+1=6"])
    assert [r.verdict for r in rows] == [VALID, INVALID, VALID]


def test_sympy_identity():
    r = verify_equality("(x+1)**2", "x**2+2*x+1")
    assert r.verdict == VALID


def test_set_like_text_stays_unknown():
    r = verify_step(1, "the solution set is {1, 2} = set of roots")
    assert r.verdict == UNKNOWN


def test_long_step_stays_unknown():
    r = verify_step(1, "x=1. " + ("long prose " * 80))
    assert r.verdict == UNKNOWN
