"""Tests for dependency tagging."""

from __future__ import annotations

from src.evaluator.dependency import build_graph, descendants


def test_correct_trace_all_none():
    g = build_graph(3, first_error_step=None)
    assert g.first_root_error is None
    assert {s.tag for s in g.steps} == {"NONE"}


def test_root_and_propagated_sequential():
    g = build_graph(4, first_error_step=2)
    tags = {s.step_id: s.tag for s in g.steps}
    assert tags[2] == "ROOT"
    assert tags[3] == "PROPAGATED"
    assert tags[4] == "PROPAGATED"
    assert tags[1] == "NONE"


def test_independent_error_not_on_path():
    depends = {1: [], 2: [1], 3: [1], 4: [3]}
    g = build_graph(4, first_error_step=2, extra_error_steps=[3], depends_on=depends)
    tags = {s.step_id: s.tag for s in g.steps}
    assert tags[2] == "ROOT"
    assert tags[3] == "INDEPENDENT"
    assert tags[4] == "NONE"


def test_out_of_range_does_not_crash():
    g = build_graph(2, first_error_step=9)
    assert g.ok is False


def test_descendants():
    edges = {1: [], 2: [1], 3: [2], 4: [1]}
    assert descendants(edges, 1) == {2, 3, 4}
    assert descendants(edges, 2) == {3}
