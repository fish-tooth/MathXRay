"""Smoke tests for the Streamlit app: the R1 demo path must render cleanly.

Uses Streamlit's AppTest so the whole page is executed headlessly. Only the
offline demo path is exercised — no Hy3 quota is consumed.
"""
from __future__ import annotations

from pathlib import Path

import pytest

APP = Path(__file__).resolve().parent.parent / "app.py"

st_testing = pytest.importorskip("streamlit.testing.v1")
AppTest = st_testing.AppTest


def _run_app():
    at = AppTest.from_file(str(APP), default_timeout=120)
    at.run()
    assert not at.exception, f"app raised: {at.exception}"
    return at


def _markdown_text(at) -> str:
    return "\n".join(m.value for m in at.markdown)


def test_app_r1_demo_renders() -> None:
    at = _run_app()
    joined = _markdown_text(at)
    assert 'class="mx-title">MathXRay</div>' in joined
    assert "① 独立求解" in joined
    assert "② 逐段审查" in joined


def test_app_page_text_has_no_parenthetical_explanations() -> None:
    """Interactive labels and stage headings must stay free of (...) glosses."""
    at = _run_app()
    labels = [r.label for r in at.radio] + [w.label for w in at.text_input]
    for label in labels:
        assert "（" not in label and "(" not in label, f"label still has a gloss: {label}"
    joined = _markdown_text(at)
    for heading in ("① 独立求解", "② 逐段审查", "③ 强制对抗", "④ 融合"):
        assert heading in joined


def test_app_r1_switch_to_unsupported_case() -> None:
    """The (3λ, -4λ) case must show the debate and the unsupported banner."""
    at = _run_app()
    at.radio[2].set_value(2)  # third demo case: unsupported answer
    at.run()
    assert not at.exception, f"app raised: {at.exception}"
    joined = _markdown_text(at)
    assert "③ 强制对抗" in joined
    assert "Unsupported Answer" in joined


def test_app_b0_engine_still_works() -> None:
    at = _run_app()
    at.radio[0].set_value("B0 混合审查")
    at.run()
    assert not at.exception, f"app raised: {at.exception}"


def test_app_stage_headings_have_no_parentheses() -> None:
    """The four R1 stage headings dropped their parenthetical glosses."""
    at = _run_app()
    joined = _markdown_text(at)
    for gloss in ("（私有脚手架）", "（指控 / 辩护 / 仲裁）", "（确定性）"):
        assert gloss not in joined, f"gloss still present: {gloss}"
