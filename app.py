"""MathXRay Streamlit application — Solve & Audit / Dashboard / Error Explorer."""

from __future__ import annotations

import json
import math
from pathlib import Path

import streamlit as st

from src.analysis.reporting import latest_by_sample, load_jsonl
from src.config import ConfigError, load_config
from src.factory import build_hybrid, build_reflective, build_solver, generation_config
from src.pipeline import MathXRayPipeline, ReflectivePipeline
from src.taxonomy import ERROR_TYPE_LABELS

ROOT = Path(__file__).resolve().parent
DEMO_PATH = ROOT / "data" / "demo_cases.json"
DEMO_R1_PATH = ROOT / "data" / "demo_cases_r1.json"
OFFICIAL_DIR = ROOT / "reports" / "official"
HS_COMPARE = ROOT / "reports" / "highschool_compare.json"
RAW_CANDIDATES = [
    ROOT / "results" / "raw" / "B0-DirectJudge_dev.jsonl",
    ROOT / "results" / "raw" / "B0-DirectJudge_pilot.jsonl",
]

st.set_page_config(page_title="MathXRay", page_icon="◇", layout="wide")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@600;700&family=Noto+Sans+SC:wght@400;500;600&display=swap');
:root { --brand:#1a5fb4; --ok:#188a52; --bad:#c0392b; --warn:#b45309; --line:#e5e7eb; }
html, body, [class*="css"] { font-family: "Noto Sans SC", "Segoe UI", sans-serif; }
.block-container { padding-top: 1.2rem; max-width: 1180px; }
h1, h2, h3 { font-family: "Source Serif 4", "Noto Serif SC", serif; }
.mx-hero { padding: 8px 0 18px; border-bottom: 1px solid rgba(128,128,128,.28); margin-bottom: 18px; }
.mx-hero-row { display:flex; align-items:center; gap:12px; }
.mx-logo { width:36px; height:36px; flex-shrink:0; }
.mx-kicker { color: var(--brand); font-weight: 600; letter-spacing: .04em; font-size: 13px; }
.mx-title { font-size: 34px; margin: 4px 0; }
.mx-sub { opacity: .78; font-size: 16px; }
.badge { display:inline-block; padding: 3px 10px; border-radius: 999px; font-size: 13px; font-weight: 600; }
.badge-ok { background:#e8f7ee; color: var(--ok); }
.badge-bad { background:#fdecea; color: var(--bad); }
.badge-warn { background:#fff7ed; color: var(--warn); }
.step { border: 1px solid rgba(128,128,128,.35); border-radius: 12px; padding: 12px 14px; margin-bottom: 8px; }
.step.root { border-color: #e35d5d; background: rgba(192, 57, 43, 0.18); }
.step.prop { border-color: #e2b36a; background: rgba(180, 83, 9, 0.16); }
.metric-card { border: 1px solid rgba(128,128,128,.35); border-radius: 12px; padding: 14px 16px; }
.metric-card .v { font-size: 28px; font-weight: 700; font-variant-numeric: tabular-nums; }
.metric-card .k { opacity: .7; font-size: 13px; }
.warn-banner { background: rgba(180, 83, 9, 0.18); border:1px solid #fdba74; border-radius:12px; padding:12px 16px; }
.step.invalid { border-color:#c0392b; background: rgba(192, 57, 43, 0.16); }
.step.unknown { border-color:#b45309; background: rgba(180, 83, 9, 0.14); }
.stage { border-left:3px solid var(--brand); padding:2px 0 2px 12px; margin-bottom:14px; }
.stage .h { font-weight:600; font-size:15px; }
.verdict { font-size:12px; font-weight:700; padding:2px 8px; border-radius:999px; }
.v-valid { background:#e8f7ee; color: var(--ok); }
.v-invalid { background:#fdecea; color: var(--bad); }
.v-unknown { background:#fff7ed; color: var(--warn); }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; }
.slide { padding: 2px 2px 8px; }
.slide-kicker { color: var(--brand); font-weight: 600; letter-spacing: .08em; font-size: 12px; }
.slide-title { font-family: "Source Serif 4", serif; font-size: 26px; margin: 4px 0 8px; line-height: 1.25; }
.slide-lead { font-size: 16px; line-height: 1.7; opacity: .9; margin-bottom: 12px; }
.slide-p { font-size: 14.5px; line-height: 1.7; color:#374151; margin: 0 0 10px; }
.flow-box { background:#fff; border:1px solid var(--line); border-radius:12px; padding:10px 14px; margin-bottom:8px; font-size:14.5px; line-height:1.6; }
.flow-box b { color: var(--brand); }
.flow-box.active { border-color: var(--brand); background:#eef4fb; }
.flow-box.warn { border-color:#e2b36a; background:#fff7ed; }
.flow-box.bad { border-color:#e35d5d; background:#fdecea; }
.flow-box.ok { border-color:#3da36a; background:#e8f7ee; }
.tiny { font-size:13px; opacity:.78; line-height:1.55; margin-top:4px; }
.cmp { border-collapse: collapse; width:100%; background:#fff; border-radius:12px; overflow:hidden; }
.cmp th { background:#eef2f7; font-size:13px; padding:8px 10px; text-align:left; color:#4b5563; }
.cmp td { border-top:1px solid var(--line); font-size:14.5px; padding:8px 10px; }
.kv { display:grid; grid-template-columns: 1fr 1fr; gap:10px; }
.kv3 { display:grid; grid-template-columns: 1fr 1fr 1fr; gap:10px; }
.two { display:grid; grid-template-columns: 1.15fr 0.85fr; gap:12px; align-items:start; }
.chart-card { background:#fff; border:1px solid var(--line); border-radius:12px; padding:8px 12px 6px; }
.chart-card .cap { font-size:13px; color:#4b5563; margin: 2px 0 6px; }
.vbars { display:flex; gap:22px; align-items:flex-end; height:210px; padding: 8px 8px 0; }
.vgroup { flex:1; text-align:center; }
.vpair { display:flex; gap:7px; align-items:flex-end; justify-content:center; height:168px; }
.vbar { width:26px; border-radius:6px 6px 0 0; position:relative; min-height:4px; }
.vbar span { position:absolute; top:-18px; left:50%; transform:translateX(-50%); font-size:11px; color:#374151; white-space:nowrap; }
.vbar.b0 { background:#94a3b8; }
.vbar.r1 { background:#1a5fb4; }
.vlbl { font-size:12px; line-height:1.35; color:#4b5563; margin-top:6px; }
.hbar { display:grid; grid-template-columns: 168px 1fr 28px; gap:8px; align-items:center; margin:7px 0; font-size:13px; }
.hbar .track { background:#eef2f7; border-radius:999px; height:12px; overflow:hidden; }
.hbar .fill { height:12px; border-radius:999px; background:#1a5fb4; }
.legend { font-size:12px; color:#4b5563; margin: 4px 0 8px; }
.legend i { display:inline-block; width:10px; height:10px; border-radius:2px; margin:0 5px 0 10px; }
.pager { text-align:right; font-size:12px; color:#9ca3af; margin-top:8px; }
.pills { display:flex; align-items:center; gap:8px; margin: 0 0 12px; flex-wrap:wrap; }
.pill { padding:4px 12px; border-radius:999px; font-size:13px; border:1px solid var(--line); background:#fff; color:#4b5563; }
.pill.on { background:#eef4fb; border-color: var(--brand); color: var(--brand); font-weight:600; }
.arr { color:#9ca3af; font-size:13px; }
.brandbar { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:0 0 10px; margin-bottom:10px; border-bottom:1px solid var(--line); }
.brand-left { display:flex; align-items:center; gap:10px; }
.brand-left svg { width:28px; height:28px; display:block; }
.brand-name { font-family:"Source Serif 4", serif; font-size:20px; font-weight:700; color:#1a5fb4; line-height:1; }
.brand-tag { font-size:12px; color:#6b7280; margin-left:8px; font-weight:500; }
.brand-sec { font-size:12px; color:var(--brand); font-weight:600; letter-spacing:.06em; }
.app-frame { border:1px solid var(--line); border-radius:14px; background:#fff; padding:12px 14px 10px; }
.app-bar { font-size:12px; color:#6b7280; margin-bottom:8px; }
.app-q { background:#f7f8fb; border-radius:8px; padding:8px 12px; font-size:14px; line-height:1.55; margin-bottom:10px; }
.app-metrics { display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-bottom:10px; }
.app-metrics .metric-card { padding:10px 12px; }
.app-metrics .v { font-size:22px; }
</style>
""",
    unsafe_allow_html=True,
)


def _load_demo() -> list[dict]:
    if not DEMO_PATH.exists():
        return []
    return json.loads(DEMO_PATH.read_text(encoding="utf-8")).get("cases", [])


def _load_demo_r1() -> list[dict]:
    """R1 demo cases: full four-pass traces captured offline (scripted mock)."""
    if not DEMO_R1_PATH.exists():
        return []
    return json.loads(DEMO_R1_PATH.read_text(encoding="utf-8")).get("cases", [])


def _load_hs_compare() -> dict | None:
    if HS_COMPARE.exists():
        return json.loads(HS_COMPARE.read_text(encoding="utf-8"))
    return None


def _load_official() -> dict | None:
    path = OFFICIAL_DIR / "processbench_three_datasets.json"
    alt = OFFICIAL_DIR / "processbench_overall.json"
    for p in (path, alt):
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return None


LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32" aria-hidden="true">'
    '<rect width="32" height="32" rx="8" fill="#1a5fb4"/>'
    '<path d="M16 5 L27 16 L16 27 L5 16 Z" fill="none" stroke="#fff" stroke-width="2.2" stroke-linejoin="round"/>'
    '<circle cx="16" cy="16" r="3.2" fill="#fff"/>'
    '<path d="M16 9.5 V13.2 M16 18.8 V22.5 M9.5 16 H13.2 M18.8 16 H22.5" stroke="#c5d8f0" stroke-width="1.4" stroke-linecap="round"/>'
    "</svg>"
)


def _hero(kicker: str, title: str, sub: str) -> None:
    st.markdown(
        f'<div class="mx-hero"><div class="mx-hero-row">'
        f'<div class="mx-logo">{LOGO_SVG}</div><div>'
        f'<div class="mx-kicker">{kicker}</div>'
        f'<div class="mx-title">{title}</div>'
        f'<div class="mx-sub">{sub}</div>'
        f"</div></div></div>",
        unsafe_allow_html=True,
    )


def _badge(ok: bool | None, yes: str, no: str) -> str:
    if ok is True:
        return f'<span class="badge badge-ok">{yes}</span>'
    if ok is False:
        return f'<span class="badge badge-bad">{no}</span>'
    return '<span class="badge">UNKNOWN</span>'


def _fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def page_solve() -> None:
    _hero(
        "SOLVE &amp; AUDIT",
        "MathXRay",
        "Hy3 写出步骤；R1 先独立做一遍，再逐段审查，必要时进入指控 / 辩护 / 仲裁，最后按固定规则汇总。",
    )
    q_engine = str(st.query_params.get("demo_engine", "") or st.query_params.get("engine", "")).lower()
    raw_case = st.query_params.get("demo_case", st.query_params.get("case", None))
    try:
        q_case = int(raw_case) if raw_case is not None and str(raw_case) != "" else None
    except (TypeError, ValueError):
        q_case = None

    if q_engine:
        use_r1 = q_engine.startswith("r1")
        if use_r1:
            cases = _load_demo_r1()
            if not cases:
                st.warning("未找到演示案例。")
                return
            idx = max(0, min(q_case or 0, len(cases) - 1))
            case = cases[idx]
            st.text_area("题目", case["problem"], height=70, disabled=True)
            _render_r1(
                steps=case["steps"],
                student_answer=case["student_answer"],
                answer_ok=case["answer_verdict"] == "EQUIVALENT",
                pred=case["audit"],
                unsupported=bool(case["unsupported_answer"]),
                title=case["headline"],
            )
            return
        cases = _load_demo()
        idx = max(0, min(q_case or 0, len(cases) - 1))
        case = cases[idx]
        sol, audit = case["solution"], case["audit"]
        st.text_area("题目", case["problem"], height=70, disabled=True)
        _render_audit(
            final_answer=sol["final_answer"],
            answer_ok=case["answer_verdict"] == "EQUIVALENT",
            process_correct=audit["process_correct"],
            first_error=audit.get("first_error_step"),
            error_type=audit.get("error_type"),
            unsupported=bool(audit.get("unsupported_answer")),
            reason=audit.get("reason", ""),
            steps=sol["solution_steps"],
            step_meta=audit["steps"],
        )
        return

    engine = st.radio(
        "评估引擎",
        ["R1 反思式审查", "B0 混合审查"],
        horizontal=True,
    )
    use_r1 = engine.startswith("R1")
    mode = st.radio(
        "输入方式",
        ["演示案例", "现场调用 Hy3"],
        horizontal=True,
    )

    if mode.startswith("演示"):
        if use_r1:
            cases = _load_demo_r1()
            if not cases:
                st.warning(
                    "未找到 `data/demo_cases_r1.json`。"
                    "请先运行 `python scripts/prepare_demo_r1.py`。"
                )
                return
            labels = [c["title"] for c in cases]
            idx = st.radio("选择案例", range(len(labels)), format_func=lambda i: labels[i])
            case = cases[idx]
            st.text_area("题目", case["problem"], height=90, disabled=True)
            _render_r1(
                steps=case["steps"],
                student_answer=case["student_answer"],
                answer_ok=case["answer_verdict"] == "EQUIVALENT",
                pred=case["audit"],
                unsupported=bool(case["unsupported_answer"]),
                title=case["headline"],
            )
            return

        cases = _load_demo()
        labels = [c["title"] for c in cases]
        default_case = 0
        try:
            default_case = max(0, min(len(cases) - 1, int(st.query_params.get("case", 0))))
        except (TypeError, ValueError):
            default_case = 0
        idx = st.radio(
            "选择案例",
            range(len(labels)),
            index=default_case,
            format_func=lambda i: labels[i],
        )
        case = cases[idx]
        sol = case["solution"]
        audit = case["audit"]
        st.markdown(f"**{case['headline']}**")
        st.text_area("题目", case["problem"], height=90, disabled=True)
        _render_audit(
            final_answer=sol["final_answer"],
            answer_ok=case["answer_verdict"] == "EQUIVALENT",
            process_correct=audit["process_correct"],
            first_error=audit.get("first_error_step"),
            error_type=audit.get("error_type"),
            unsupported=bool(audit.get("unsupported_answer")),
            reason=audit.get("reason", ""),
            steps=sol["solution_steps"],
            step_meta=audit["steps"],
        )
        return

    problem = st.text_area("输入数学题", height=120, placeholder="例如：半径为 3 的圆的面积是多少？")
    gold = st.text_input("标准答案")
    if st.button("求解并审计", type="primary", disabled=not problem.strip()):
        try:
            config = load_config(ROOT / "configs" / "default.yaml")
            if use_r1:
                pipe = ReflectivePipeline(
                    build_solver(config, "hy3"), build_reflective(config, "hy3")
                )
            else:
                pipe = MathXRayPipeline(
                    build_solver(config, "hy3"), build_hybrid(config, "hy3")
                )
            with st.spinner("Hy3 解题并审计中…"):
                result = pipe.run(
                    problem.strip(),
                    gold_answer=gold.strip() or None,
                    gen_cfg=generation_config(config),
                )
        except (ConfigError, SystemExit) as exc:
            st.error(f"无法调用 Hy3：{exc}。请配置 `.env` 中的 HY3_API_KEY / HY3_MODEL，或改用演示案例。")
            return
        except Exception as exc:  # noqa: BLE001
            st.error(f"运行失败：{exc}")
            return
        if use_r1:
            _render_r1_live(result)
        else:
            _render_live(result)


def _render_r1_live(result) -> None:
    sol = result.solver.solution
    if sol is None:
        st.error(result.solver.parse_error or result.solver.error or "解析失败")
        if result.solver.raw:
            st.code(result.solver.raw[:4000])
        return
    pred = result.prediction
    if pred is None:
        st.warning("未产生 R1 判定。")
        return
    if pred.error:
        st.error(f"R1 审查未完成：{pred.error}")
        st.info("若为额度问题 HTTP 402，请在控制台开通后付费，或改用演示案例。")
        return
    _render_r1(
        steps=result.steps,
        student_answer=sol.final_answer,
        answer_ok=result.answer.is_equivalent if result.answer else None,
        pred=pred.to_dict(),
        unsupported=bool(result.unsupported_answer),
    )


def _render_audit(
    *,
    final_answer: str,
    answer_ok: bool | None,
    process_correct: bool | None,
    first_error,
    error_type: str | None,
    unsupported: bool,
    reason: str,
    steps: list,
    step_meta: list,
    confidence: str | None = None,
) -> None:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div class="metric-card"><div class="k">最终答案</div>'
            f'<div class="v">{final_answer}</div>'
            f'{_badge(answer_ok, "与标准答案一致", "与标准答案不一致")}</div>',
            unsafe_allow_html=True,
        )
    with c2:
        label = "成立" if process_correct else "不成立" if process_correct is False else "未知"
        st.markdown(
            f'<div class="metric-card"><div class="k">过程判定</div>'
            f'<div class="v">{label}</div>'
            f'{_badge(process_correct, "Process ✓", "Process ✗")}</div>',
            unsafe_allow_html=True,
        )
    with c3:
        first = first_error or "—"
        etype = ERROR_TYPE_LABELS.get(error_type or "", error_type or "无")
        st.markdown(
            f'<div class="metric-card"><div class="k">最早错误 / 根因</div>'
            f'<div class="v">Step {first}</div>'
            f'<span class="badge">{etype}</span></div>',
            unsafe_allow_html=True,
        )
    if unsupported:
        st.markdown(
            '<div class="warn-banner"><b>Unsupported Answer</b>：最终答案正确，'
            "但推理过程无法支撑该结论。</div>",
            unsafe_allow_html=True,
        )
    extra = f" · 置信度 {confidence}" if confidence else ""
    st.caption((reason or "") + extra)
    if confidence == "Low":
        st.info("建议人工复核：符号证据与语义审查不一致。")
    st.subheader("逐步审计")
    meta_by_id = {}
    for item in step_meta:
        if isinstance(item, dict):
            meta_by_id[item.get("step_id")] = item
        else:
            meta_by_id[item.step_id] = {
                "tag": item.dependency_tag,
                "fused": item.fused_verdict,
                "symbolic": item.symbolic_verdict,
                "evidence": item.evidence,
            }
    for step in steps:
        if isinstance(step, dict):
            sid = step["step_id"]
            statement = step["statement"]
            expression = step.get("expression")
        else:
            sid = step.step_id
            statement = step.statement
            expression = step.expression
        meta = meta_by_id.get(sid, {})
        tag = meta.get("tag", "NONE")
        klass = "root" if tag == "ROOT" else "prop" if tag == "PROPAGATED" else ""
        fused = meta.get("fused", "")
        expr_html = f" &nbsp; <code>{expression}</code>" if expression else ""
        st.markdown(
            f'<div class="step {klass}"><b>Step {sid}</b> · {tag} · {fused}<br>'
            f"{statement}{expr_html}</div>",
            unsafe_allow_html=True,
        )


def _render_live(result) -> None:
    sol = result.solver.solution
    if sol is None:
        st.error(result.solver.parse_error or result.solver.error or "解析失败")
        if result.solver.raw:
            st.code(result.solver.raw[:4000])
        return
    audit = result.audit
    answer_ok = result.answer.is_equivalent if result.answer else None
    _render_audit(
        final_answer=sol.final_answer,
        answer_ok=answer_ok,
        process_correct=audit.process_correct if audit else None,
        first_error=audit.first_error_step if audit else None,
        error_type=audit.error_type if audit else None,
        unsupported=bool(result.unsupported_answer),
        reason=audit.reason if audit else "",
        steps=sol.solution_steps,
        step_meta=list(audit.step_audits) if audit else [],
        confidence=audit.confidence if audit else None,
    )


def _verdict_badge(verdict: str) -> str:
    v = (verdict or "").upper()
    cls = "v-valid" if v == "VALID" else "v-invalid" if v == "INVALID" else "v-unknown"
    return f'<span class="verdict {cls}">{v or "N/A"}</span>'


def _render_r1(
    *,
    steps: list[str],
    student_answer: str,
    answer_ok: bool | None,
    pred: dict,
    unsupported: bool,
    title: str = "",
) -> None:
    """Render an R1 judgement including its four-pass trace."""
    if title:
        st.markdown(f"**{title}**")
    extra = pred.get("extra") or {}
    process_correct = pred.get("process_correct")
    first_error = pred.get("first_error_step")
    error_type = pred.get("error_type")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div class="metric-card"><div class="k">最终答案</div>'
            f'<div class="v">{student_answer}</div>'
            f'{_badge(answer_ok, "与标准答案一致", "与标准答案不一致")}</div>',
            unsafe_allow_html=True,
        )
    with c2:
        label = "成立" if process_correct else "不成立" if process_correct is False else "未知"
        st.markdown(
            f'<div class="metric-card"><div class="k">过程判定</div>'
            f'<div class="v">{label}</div>'
            f'{_badge(process_correct, "Process ✓", "Process ✗")}</div>',
            unsafe_allow_html=True,
        )
    with c3:
        etype = ERROR_TYPE_LABELS.get(error_type or "", error_type or "无")
        st.markdown(
            f'<div class="metric-card"><div class="k">最早错误 / 类型</div>'
            f'<div class="v">Step {first_error or "—"}</div>'
            f'<span class="badge">{etype}</span></div>',
            unsafe_allow_html=True,
        )

    if unsupported:
        st.markdown(
            '<div class="warn-banner"><b>Unsupported Answer</b>：最终答案正确，'
            "但推理过程无法支撑该结论——这正是只核对答案会漏掉的一类样本。</div>",
            unsafe_allow_html=True,
        )

    st.subheader("R1 流程追踪")

    # Pass 1 — independent solve (private scaffold, never shown as gold).
    ind = extra.get("independent") or {}
    outline = ind.get("outline") or []
    outline_html = "".join(f"<li>{o}</li>" for o in outline)
    st.markdown(
        '<div class="stage"><div class="h">① 独立求解</div>'
        '<div class="mono">学生步骤不可见 · 只用来对照</div>'
        f'<div>独立结论：<b>{ind.get("final_answer") or "—"}</b></div>'
        f'<ul>{outline_html}</ul></div>',
        unsafe_allow_html=True,
    )

    # Pass 2 — per-paragraph critique.
    sw = extra.get("stepwise") or {}
    rows = {r.get("step_id"): r for r in (sw.get("steps") or [])}
    step_html = []
    for i, text in enumerate(steps, start=1):
        row = rows.get(i) or {}
        verdict = row.get("verdict") or "UNKNOWN"
        klass = "invalid" if verdict == "INVALID" else "unknown" if verdict == "UNKNOWN" else ""
        claim = row.get("claim") or ""
        step_html.append(
            f'<div class="step {klass}"><b>Step {i}</b> &nbsp;{_verdict_badge(verdict)}<br>'
            f"{text}"
            + (f'<br><span class="mono">{claim}</span>' if claim else "")
            + "</div>"
        )
    st.markdown(
        '<div class="stage"><div class="h">② 逐段审查</div>'
        f'{"".join(step_html)}</div>',
        unsafe_allow_html=True,
    )

    # Pass 3/4 — adversarial debate, only when forced.
    triggers = extra.get("triggers") or []
    debate = extra.get("debate") or {}
    if extra.get("debate_triggered"):
        trigger_html = " ".join(f'<span class="badge badge-warn">{t}</span>' for t in triggers)
        acc = debate.get("accuser") or {}
        dfn = debate.get("defender") or {}
        arb = debate.get("arbiter") or {}
        parts = [
            '<div class="stage"><div class="h">③ 指控 / 辩护 / 仲裁</div>',
            f"<div>触发条件：{trigger_html}</div>",
            f'<div class="step invalid"><b>指控</b> · Step {acc.get("first_error_step")} · '
            f'{ERROR_TYPE_LABELS.get(acc.get("error_type") or "", acc.get("error_type") or "—")}'
            f'<br>{acc.get("charge") or "—"}',
        ]
        if acc.get("counterexample"):
            parts.append(f'<br><span class="mono">反例：{acc["counterexample"]}</span>')
        parts.append("</div>")
        rebuts = dfn.get("rebuts")
        badge = "未反驳" if rebuts is False else "反驳成立" if rebuts is True else "无效"
        parts.append(
            f'<div class="step"><b>辩护</b> · <span class="badge">{badge}</span>'
            f'<br>{dfn.get("reason") or "—"}</div>'
        )
        if arb:
            arb_label = "过程不成立" if arb.get("process_correct") is False else "过程成立"
            parts.append(
                f'<div class="step {"invalid" if arb.get("process_correct") is False else ""}">'
                f"<b>仲裁</b> · {arb_label} · Step {arb.get('first_error_step') or '—'}"
                f'<br>{arb.get("reason") or "—"}</div>'
            )
        parts.append("</div>")
        st.markdown("".join(parts), unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="stage"><div class="h">③ 指控 / 辩护 / 仲裁</div>'
            '<div class="mono">未触发：独立结论一致、逐步审查无 UNKNOWN、'
            "答案校验通过。</div></div>",
            unsafe_allow_html=True,
        )

    # Fusion.
    sym = extra.get("symbolic_first_invalid")
    st.markdown(
        '<div class="stage"><div class="h">④ 融合</div>'
        f'<div class="mono">符号 INVALID 优先；答案核失败时禁止再判过程成立。</div>'
        f'<div>符号首个 INVALID：<b>Step {sym or "—"}</b></div>'
        f'<div>结论：{pred.get("reason") or "—"}</div></div>',
        unsafe_allow_html=True,
    )
    st.caption(f"R1 调用次数：{extra.get('n_calls', '—')} · 方法：{extra.get('method', 'R1')}")


def page_dashboard() -> None:
    _hero(
        "BENCHMARK DASHBOARD",
        "MathXRay 评测看板",
        "GSM8K + MATH + Omni-MATH。数字来自 reports/official/，由原始记录重算。",
    )
    data = _load_official()
    if not data:
        st.warning("尚未生成正式结果。请先运行 `python scripts/aggregate_official.py`。")
        return
    m = data.get("metrics") or {}
    ci = data.get("ci") or {}
    cols = st.columns(4)
    cards = [
        ("M2 First-Error Exact", m.get("first_error_exact"), ci.get("first_error_exact", {}).get("fmt")),
        ("M1 Error Detection", m.get("error_detection_recall"), ci.get("error_detection_recall", {}).get("fmt")),
        ("M3 Correct-process Acc", m.get("correct_process_accuracy"), ci.get("correct_process_accuracy", {}).get("fmt")),
        ("M5 Official Composite", m.get("official_composite"), None),
    ]
    n_show = m.get("n_all", data.get("n"))
    for col, (name, val, extra) in zip(cols, cards, strict=False):
        with col:
            foot = extra or f"n={n_show}"
            st.markdown(
                f'<div class="metric-card"><div class="k">{name}</div>'
                f'<div class="v">{_fmt(val)}</div><div class="k">{foot}</div></div>',
                unsafe_allow_html=True,
            )

    st.subheader("按数据集 / 难度")
    rows = []
    for src, row in sorted((data.get("per_source") or {}).items()):
        rows.append(
            {
                "source": src,
                "M1": _fmt(row.get("error_detection_recall")),
                "M2 Exact": _fmt(row.get("first_error_exact")),
                "M3 Correct": _fmt(row.get("correct_process_accuracy")),
                "M5": _fmt(row.get("official_composite")),
                "n": row.get("n_all"),
            }
        )
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
        m2_chart = {
            src: float(row.get("first_error_exact") or 0)
            for src, row in sorted((data.get("per_source") or {}).items())
        }
        st.bar_chart(m2_chart)

    dist = data.get("error_type_distribution") or {}
    if dist:
        st.subheader("预测错误类型分布")
        labels = data.get("error_type_labels") or ERROR_TYPE_LABELS
        st.bar_chart({labels.get(k, k): v for k, v in dist.items()})

    uns = data.get("unsupported") or {}
    if uns:
        st.subheader("答案正确但过程不成立")
        st.write(
            f"Gold unsupported answers: **{uns.get('n_unsupported_answer')}** · "
            f"Recall: **{_fmt(uns.get('unsupported_recall'))}**"
        )
    bound = data.get("capability_boundary") or {}
    if bound:
        st.info(
            f"能力边界：First-Error Exact 最大相邻降幅发生在 "
            f"{bound.get('from_difficulty')} ({bound.get('from')}) → "
            f"{bound.get('to_difficulty')} ({bound.get('to')})，"
            f"降幅 {_fmt(bound.get('drop'))}。"
        )

    hs = _load_hs_compare()
    if hs:
        st.markdown("---")
        st.subheader("私有高中题集（本地，不外发）")
        st.caption(
            "约 4300 道高中题的冻结切片 n=88。没有逐步对错的人工标注；"
            "答案对不上只说明过程有问题，改错样本才能看步号。"
        )
        b0, r1 = hs.get("b0") or {}, hs.get("r1") or {}
        h1, h2, h3, h4 = st.columns(4)
        cards_hs = [
            ("答案错误 · 发现有错", r1.get("qwen_wrong_m1"), f"B0 {b0.get('qwen_wrong_n')} → R1 {r1.get('qwen_wrong_n')}"),
            ("改错样本 · 步号一致", r1.get("adversarial_m2"), f"B0 {b0.get('adversarial_m2_n')} → R1 {r1.get('adversarial_m2_n')}"),
            ("官方详解 · 认为成立", r1.get("official_m3"), f"B0 {b0.get('official_n')} → R1 {r1.get('official_n')}"),
            ("两者调和平均", r1.get("probe_f1"), f"B0 {_fmt(b0.get('probe_f1'))}"),
        ]
        for col, (name, val, foot) in zip((h1, h2, h3, h4), cards_hs, strict=False):
            with col:
                st.markdown(
                    f'<div class="metric-card"><div class="k">{name}</div>'
                    f'<div class="v">{_fmt(val)}</div><div class="k">{foot}</div></div>',
                    unsafe_allow_html=True,
                )
        import pandas as pd

        st.bar_chart(
            pd.DataFrame(
                {
                    "B0": [
                        float(b0.get("qwen_wrong_m1") or 0),
                        float(b0.get("adversarial_m2") or 0),
                        float(b0.get("official_m3") or 0),
                    ],
                    "R1": [
                        float(r1.get("qwen_wrong_m1") or 0),
                        float(r1.get("adversarial_m2") or 0),
                        float(r1.get("official_m3") or 0),
                    ],
                },
                index=["答案错·发现有错", "改错·步号一致", "详解·认为成立"],
            )
        )
        st.info(
            f"R1 在答案错误样本上的 1.00，大约 {r1.get('gate_flips')} 条是「答案已经对不上」这条规则改判的，"
            f"逐步审查自己标错大约 {r1.get('stepwise_only_m1')}。"
            "总账（调和平均）R1 0.50，略低于 B0 0.54：更会抓错，也更容易把官方详解判严。"
        )

    full_path = OFFICIAL_DIR / "processbench_full_replay.json"
    if full_path.exists():
        full = json.loads(full_path.read_text(encoding="utf-8"))
        st.subheader("B0 vs Full 符号融合回放")
        st.write(
            {
                "B0 M2": (full.get("B0") or {}).get("first_error_exact"),
                "Full M2": (full.get("Full") or {}).get("first_error_exact"),
                "Δ": full.get("delta_first_error_exact"),
                "n": full.get("n"),
            }
        )


def page_explorer() -> None:
    _hero(
        "ERROR EXPLORER",
        "MathXRay 错误探索",
        "筛选来源、过程状态与错误类型。样本 ID 与 raw JSONL 对齐。",
    )
    raw_path = next((p for p in RAW_CANDIDATES if p.exists()), None)
    if raw_path is None:
        st.warning("未找到 `results/raw/B0-DirectJudge_*.jsonl`。")
        return
    records = latest_by_sample(load_jsonl(raw_path))
    sources = sorted({r.get("source") or "" for r in records})
    c1, c2, c3 = st.columns(3)
    source = c1.multiselect("来源", sources, default=sources)
    status = c2.selectbox("过程状态", ["全部", "Gold 错误", "Gold 正确", "预测误报", "定位偏差"])
    etype = c3.text_input("错误类型包含")

    def keep(rec: dict) -> bool:
        if rec.get("source") not in source:
            return False
        gold_ok = rec.get("gold_process_correct")
        pred = rec.get("prediction") or {}
        if status == "Gold 错误" and gold_ok:
            return False
        if status == "Gold 正确" and not gold_ok:
            return False
        if status == "预测误报" and not (gold_ok and pred.get("process_correct") is False):
            return False
        if status == "定位偏差":
            if gold_ok or pred.get("process_correct") is not False:
                return False
            if pred.get("first_error_step") == rec.get("gold_first_error_step"):
                return False
        if etype and etype.upper() not in str(pred.get("error_type") or "").upper():
            return False
        return True

    shown = [r for r in records if keep(r)]
    st.caption(f"{raw_path.name} · 显示 {len(shown)} / {len(records)}")
    table = []
    for r in shown[:400]:
        pred = r.get("prediction") or {}
        table.append(
            {
                "sample_id": r.get("sample_id"),
                "source": r.get("source"),
                "gold_P": r.get("gold_process_correct"),
                "gold_step": r.get("gold_first_error_step"),
                "pred_P": pred.get("process_correct"),
                "pred_step": pred.get("first_error_step"),
                "error_type": pred.get("error_type"),
                "A_correct": r.get("gold_final_answer_correct"),
                "reason": (pred.get("reason") or "")[:180],
            }
        )
    st.dataframe(table, use_container_width=True, hide_index=True)
    pick = st.selectbox("查看样本", [""] + [t["sample_id"] for t in table])
    if pick:
        rec = next(r for r in shown if r.get("sample_id") == pick)
        st.json(
            {
                "sample_id": rec.get("sample_id"),
                "source": rec.get("source"),
                "gold": {
                    "process_correct": rec.get("gold_process_correct"),
                    "first_error_step": rec.get("gold_first_error_step"),
                    "final_answer_correct": rec.get("gold_final_answer_correct"),
                },
                "prediction": rec.get("prediction"),
            }
        )


def _slide_shell(kicker: str, title: str, lead: str, body: str, page: str) -> None:
    st.markdown(
        f'<div class="slide"><div class="brandbar">'
        f'<div class="brand-left">{LOGO_SVG}<div>'
        f'<span class="brand-name">MathXRay</span>'
        f'<span class="brand-tag">数学推理过程审查</span></div></div>'
        f'<div class="brand-sec">{kicker}</div></div>'
        f'<div class="slide-title">{title}</div>'
        f'<div class="slide-lead">{lead}</div>{body}'
        f'<div class="pager">{page}</div></div>',
        unsafe_allow_html=True,
    )


def _app_metrics(answer: str, answer_ok: bool | None, process_ok: bool | None, first: str) -> str:
    a_badge = _badge(answer_ok, "与参考答案一致", "与参考答案不一致")
    p_label = "成立" if process_ok else "不成立" if process_ok is False else "未知"
    p_badge = _badge(process_ok, "Process ✓", "Process ✗")
    return (
        '<div class="app-metrics">'
        f'<div class="metric-card"><div class="k">最终答案</div><div class="v">{answer}</div>{a_badge}</div>'
        f'<div class="metric-card"><div class="k">过程判定</div><div class="v">{p_label}</div>{p_badge}</div>'
        f'<div class="metric-card"><div class="k">最早错误</div><div class="v">{first}</div></div>'
        "</div>"
    )


def _r1_flow(active: int | None) -> str:
    items = [
        (1, "① 独立求解", "先自己做一遍。此时看不到学生步骤，结论只用来对照。"),
        (2, "② 逐段审查", "每一段打 VALID / INVALID / UNKNOWN，并标出最早出错的那一步。"),
        (3, "③ 指控 · 辩护 · 仲裁", "两边结论对不上、某段说不清、或答案校验失败时才打开。"),
        (4, "④ 按规则汇总", "能用计算证伪的步骤优先；答案已经对不上时，禁止再说过程成立。"),
    ]
    parts = []
    for i, title, desc in items:
        cls = "active" if active == i else ""
        parts.append(
            f'<div class="flow-box {cls}"><b>{title}</b><div class="tiny">{desc}</div></div>'
        )
    return "".join(parts)


def _r1_pills(active: int) -> str:
    names = ["独立求解", "逐段审查", "对质", "规则汇总"]
    bits = []
    for i, name in enumerate(names, start=1):
        cls = "on" if i == active else ""
        bits.append(f'<span class="pill {cls}">{i} {name}</span>')
        if i < 4:
            bits.append('<span class="arr">→</span>')
    return f'<div class="pills">{"".join(bits)}</div>'


def _svg_pb_line() -> str:
    xs = [90, 270, 450, 630]
    names = ["GSM8K", "MATH", "Omni-MATH", "Olympiad"]

    def yy(v: float) -> float:
        return 208 - (v - 0.55) / 0.50 * 168

    series = [
        ([1.00, 1.00, 0.95, 0.91], "#188a52", "发现过程有错"),
        ([0.84, 0.81, 0.75, 0.69], "#1a5fb4", "指出最早错步"),
        ([1.00, 0.88, 0.77, 0.89], "#b45309", "放过正确过程"),
    ]
    grid = "".join(
        f'<line x1="70" y1="{yy(v):.1f}" x2="680" y2="{yy(v):.1f}" '
        f'stroke="#e5e7eb" /><text x="8" y="{yy(v) + 4:.1f}" fill="#9ca3af" '
        f'font-size="11">{v:.2f}</text>'
        for v in (0.60, 0.70, 0.80, 0.90, 1.00)
    )
    ticks = "".join(
        f'<text x="{x}" y="228" text-anchor="middle" fill="#4b5563" font-size="12">{n}</text>'
        for x, n in zip(xs, names)
    )
    paths = []
    for vals, color, _label in series:
        pts = " ".join(f"{x:.0f},{yy(v):.1f}" for x, v in zip(xs, vals))
        dots = "".join(
            f'<circle cx="{x:.0f}" cy="{yy(v):.1f}" r="4" fill="{color}"/>'
            for x, v in zip(xs, vals)
        )
        paths.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.4" points="{pts}"/>{dots}')
    legend = (
        '<i style="background:#188a52"></i>发现过程有错'
        '<i style="background:#1a5fb4"></i>指出最早错步'
        '<i style="background:#b45309"></i>放过正确过程'
    )
    return (
        '<div class="chart-card"><div class="cap">B0 一次判断 · 公开评测随难度变化</div>'
        f'<div class="legend">{legend}</div>'
        '<svg viewBox="0 0 720 240" width="100%" height="232">'
        f"{grid}{''.join(paths)}{ticks}</svg></div>"
    )


def _hs_bars() -> str:
    rows = [
        ("答案已错<br>抓住过程", 0.143, 1.000),
        ("自己改错<br>步号对上", 0.688, 0.750),
        ("官方详解<br>判过程对", 0.438, 0.375),
        ("后两项<br>折中", 0.535, 0.500),
    ]
    cols = []
    for name, b0, r1 in rows:
        cols.append(
            f'<div class="vgroup"><div class="vpair">'
            f'<div class="vbar b0" style="height:{b0 * 100:.1f}%"><span>{b0:.2f}</span></div>'
            f'<div class="vbar r1" style="height:{r1 * 100:.1f}%"><span>{r1:.2f}</span></div>'
            f'</div><div class="vlbl">{name}</div></div>'
        )
    return (
        '<div class="chart-card"><div class="cap">私有高中题集 · 同一 88 道题</div>'
        '<div class="legend"><i style="background:#94a3b8"></i>B0 一次判断'
        '<i style="background:#1a5fb4"></i>R1 四段审查</div>'
        f'<div class="vbars">{"".join(cols)}</div></div>'
    )


def _svg_radar() -> str:
    cx, cy, r = 200.0, 168.0, 108.0
    labels = ["抓住答案错", "改错步号", "放过详解", "折中"]
    b0 = [0.143, 0.688, 0.438, 0.535]
    r1 = [1.000, 0.750, 0.375, 0.500]
    n = 4

    def pt(i: int, v: float) -> tuple[float, float]:
        ang = -math.pi / 2 + i * 2 * math.pi / n
        return cx + r * v * math.cos(ang), cy + r * v * math.sin(ang)

    rings = []
    for g in (0.25, 0.5, 0.75, 1.0):
        pts = " ".join(f"{pt(i, g)[0]:.1f},{pt(i, g)[1]:.1f}" for i in range(n))
        rings.append(f'<polygon points="{pts}" fill="none" stroke="#e5e7eb"/>')
    axes = []
    labs = []
    for i, name in enumerate(labels):
        x, y = pt(i, 1.0)
        axes.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        lx, ly = pt(i, 1.22)
        labs.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" font-size="12" fill="#374151">{name}</text>'
        )

    def poly(
        vals: list[float], color: str, fill_a: str, width: str = "2.4", extra: str = ""
    ) -> str:
        pts = " ".join(f"{pt(i, v)[0]:.1f},{pt(i, v)[1]:.1f}" for i, v in enumerate(vals))
        return (
            f'<polygon points="{pts}" fill="{fill_a}" stroke="{color}" '
            f'stroke-width="{width}" {extra}/>'
            + "".join(
                f'<circle cx="{pt(i, v)[0]:.1f}" cy="{pt(i, v)[1]:.1f}" r="3.6" fill="{color}"/>'
                for i, v in enumerate(vals)
            )
        )

    dash = "stroke-dasharray='5 4'"
    return (
        '<div class="chart-card"><div class="cap">四项合在一张雷达图里看形状</div>'
        '<div class="legend"><i style="background:#475569"></i>B0'
        '<i style="background:#1a5fb4"></i>R1</div>'
        '<svg viewBox="0 0 420 340" width="100%" height="248">'
        f"{''.join(rings)}{''.join(axes)}"
        f"{poly(r1, '#1a5fb4', 'rgba(26,95,180,.16)')}"
        f"{poly(b0, '#475569', 'none', '2.2', dash)}"
        f"{''.join(labs)}</svg></div>"
    )


def _hs_gate() -> str:
    rows = [
        ("逐步标出 INVALID", 5, "#188a52"),
        ("答案对不上才改判", 18, "#1a5fb4"),
        ("逐步 UNKNOWN", 5, "#b45309"),
        ("漏掉", 0, "#c0392b"),
    ]
    bars = []
    for name, n, color in rows:
        w = n / 28 * 100
        bars.append(
            f'<div class="hbar"><div>{name}</div>'
            f'<div class="track"><div class="fill" style="width:{w:.1f}%;background:{color}"></div></div>'
            f"<div>{n}</div></div>"
        )
    return (
        '<div class="chart-card"><div class="cap">R1 抓住全部 28 道「答案已经算错」的题，拆开看来源</div>'
        f"{''.join(bars)}"
        '<div class="tiny">共 28 道。检出率 1.00 主要来自「答案已经对不上，过程就不能再判成立」这条规则。</div></div>'
    )


def page_story(slide: int) -> None:
    """Full-page slides for the demo GIF: framework → app → numbers."""
    slides: list[tuple[str, str, str, str]] = [
        (
            "介绍",
            "过程审查看什么",
            "模型会写出一串步骤。MathXRay 要回答两件事：过程能不能站住；如果站不住，错从哪一步进来。",
            '<div class="kv3">'
            '<div class="flow-box"><b>解题</b><div class="tiny">Hy3 按段落写出推理，并给出最终答案。</div></div>'
            '<div class="flow-box"><b>核对答案</b><div class="tiny">最终答案和参考答案能否对上。对得上只说明结果对。</div></div>'
            '<div class="flow-box"><b>审查过程</b><div class="tiny">逐步看推理是否成立，标出最早错误和后面跟着错的步骤。</div></div>'
            "</div>"
            '<div class="kv">'
            '<div class="flow-box"><b>前面</b><div class="tiny">算法怎么跑：一次判断（B0）和四段审查（R1）。</div></div>'
            '<div class="flow-box"><b>后面</b><div class="tiny">应用里的三道例题，公开评测和私有高中集上的结果。</div></div>'
            "</div>",
        ),
        (
            "问题",
            "只看答案会漏掉什么",
            "答案对了，过程仍可能有问题。下面三类在只核答案时都会漏掉。",
            '<div class="flow-box bad"><b>中间算错</b><div class="tiny">'
            "公式写对了，乘法写成 12×5=70。后面每一步都顺着 70 往下写。</div></div>"
            '<div class="flow-box warn"><b>公式错了，数字碰巧对</b><div class="tiny">'
            "用了错误公式，中间还绕了一圈，最后数字却和参考答案对上了。</div></div>"
            '<div class="flow-box"><b>写完了，题目要的东西还没收齐</b><div class="tiny">'
            "题目要非零共线向量，解答写成 (3λ,−4λ) 且没排除 λ=0。局部等式成立，形式不完整。</div></div>",
        ),
        (
            "总流程",
            "从解题到出报告",
            "整条链路按固定顺序走。每一步都留下记录，后面的步骤读前面的产出。",
            '<div class="flow-box"><b>1 · 解题</b> Hy3 把解答拆成若干段落，每段有一句陈述，必要时带表达式，最后给出答案。</div>'
            '<div class="flow-box"><b>2 · 核答案</b> 把学生答案和参考答案做等价判断。对不上，说明过程里至少有一处问题；对得上，过程仍可能撑不住。</div>'
            '<div class="flow-box"><b>3 · 审过程</b> B0 一次给出结论；R1 先自己做、再逐段看、必要时对质，最后按规则汇总。</div>'
            '<div class="flow-box"><b>4 · 出报告</b> 过程是否成立、最早错在第几步、错误类型、后面哪些步骤只是被带着错。</div>',
        ),
        (
            "产出",
            "审查结果里有什么",
            "后面的评测都对着这四项来。缺一项，数字就对不上。",
            '<div class="kv">'
            '<div class="flow-box"><b>过程是否成立</b><div class="tiny">整份解答能不能从题目推到结论。成立 / 不成立 / 说不清。</div></div>'
            '<div class="flow-box"><b>最早错误步号</b><div class="tiny">错从哪一段进来。后面跟着错的步骤另标，不另算一个首错。</div></div>'
            '<div class="flow-box"><b>错误类型</b><div class="tiny">计算、概念、形式不完整等。方便按类型看失败模式。</div></div>'
            '<div class="flow-box"><b>跟着错的步骤</b><div class="tiny">本身没有新错误，只是沿用了前面的错数或错式。</div></div>'
            "</div>",
        ),
        (
            "B0",
            "一次看完就给结论",
            "把题目和学生步骤一次性交给模型，直接给出过程对不对、第几步、什么类型。",
            '<div class="flow-box">做法简单，调用次数少。公开评测上用的就是这套。一次生成里要同时完成「有没有错」和「错在第几步」，形式不完整的解答比较容易被放过。</div>'
            '<div class="kv">'
            '<div class="flow-box ok"><b>适合</b><div class="tiny">批量打分、先看整体水平、调用次数需要控制的时候。</div></div>'
            '<div class="flow-box warn"><b>比较吃力</b><div class="tiny">停在参数族、答案碰巧对、中间一步算错但后文写得很顺。</div></div>'
            "</div>",
        ),
        (
            "R1 · 总览",
            "把审查拆成四段",
            "每一段只干一件事。后面的段可以读前面的产出；独立求解看不到学生步骤。",
            _r1_flow(None)
            + '<p class="slide-p">和 B0 的差别：先自己做一遍当对照，再按段落表态；两边对不上才进入对质。'
            "最后按固定规则给出结论。</p>",
        ),
        (
            "R1 · 第 1 段",
            "先自己做一遍",
            "这一段的输入只有题目。学生写了什么、参考答案是什么，都还看不到。",
            _r1_pills(1)
            + '<div class="kv">'
            '<div class="flow-box"><b>输入</b><div class="tiny">只有题干。学生步骤、参考答案都不在提示里。</div></div>'
            '<div class="flow-box"><b>产出</b><div class="tiny">一份独立答案，外加几条简要思路，后面当对照用。</div></div>'
            '<div class="flow-box"><b>怎么用</b><div class="tiny">和学生答案差很远，就提高「过程有问题」的嫌疑，后面更容易进入对质。</div></div>'
            '<div class="flow-box"><b>不写进提示的</b><div class="tiny">参考答案全程不进审查提示，避免模型对着答案改口。</div></div>'
            "</div>",
        ),
        (
            "R1 · 第 2 段",
            "每一段单独判断",
            "现在才第一次看见学生步骤。每一段只评这一段新引入的对错。",
            _r1_pills(2)
            + '<div class="kv3">'
            '<div class="flow-box ok"><b>VALID</b><div class="tiny">这一段本身站得住，没有引入新错误。</div></div>'
            '<div class="flow-box bad"><b>INVALID</b><div class="tiny">这一段引入了错误。若前面都还对，它就是最早错误。</div></div>'
            '<div class="flow-box warn"><b>UNKNOWN</b><div class="tiny">材料不够、式子含糊，这一段说不清。后面往往要对质。</div></div>'
            "</div>"
            '<p class="slide-p">前面已经错了，后面顺着错数往下写，标成跟着错，不再另开一个首错。第一个 INVALID 进入汇总。</p>',
        ),
        (
            "R1 · 定位",
            "错从哪一步进来",
            "审查停在引入错误的那一步。最后写出答案的那一步，常常只是把错的数抄下去。",
            '<div class="flow-box ok"><b>最早错误</b><div class="tiny">从这一段开始，推理离开了正确轨道。公开评测里的「步号一致」，指的就是它。</div></div>'
            '<div class="flow-box warn"><b>跟着错</b><div class="tiny">段落本身没有新的计算或新的概念，只是沿用了前面的错。</div></div>'
            '<p class="slide-p">如果把最后一步也当成首错，定位能力看不出来。评测时只有指到被改的那一步才算找对。</p>',
        ),
        (
            "R1 · 完整性",
            "形式还不完整",
            "局部每一步都像对的，整份解答仍可能不合格。题目要非零向量，解答却写成任意 λ 的 (3λ,−4λ)。",
            '<div class="flow-box">等式在参数意义下成立，一次判断很容易放过。'
            "R1 把「形式是否满足题意」也算进过程：没收束到题目要求的对象，过程就不成立。</div>"
            '<p class="slide-p">私有高中题里这类情况很常见。B0 在「答案已经算错」的 28 道上只抓住 4 道，'
            "多半就出在这种「写得下去、却没按题目要求收束」的解答上。</p>",
        ),
        (
            "R1 · 第 3 段",
            "什么时候才对质",
            "对质会多几次调用，所以默认关掉。下面三条至少中一条，才进入指控 / 辩护 / 仲裁。",
            _r1_pills(3)
            + '<div class="kv3">'
            '<div class="flow-box"><b>两边结论对不上</b><div class="tiny">独立求解的答案和学生答案差很远。</div></div>'
            '<div class="flow-box"><b>某段说不清</b><div class="tiny">逐步审查打了 UNKNOWN，需要再确认。</div></div>'
            '<div class="flow-box"><b>答案校验失败</b><div class="tiny">学生答案和参考答案对不上，过程里必有问题。</div></div>'
            "</div>"
            '<p class="slide-p">三条都不中，就跳过对质，直接进入汇总。'
            "矩形面积那道题会中第一条：独立求解得到 60，学生写成 70。</p>",
        ),
        (
            "R1 · 对质",
            "指控、辩护、仲裁",
            "三步读同一份材料，分工不同。谁说了算，还是留给最后的规则。",
            '<div class="flow-box bad"><b>指控</b><div class="tiny">专门找错。要指出步号、类型，最好给一个能算出来的反例，例如 12×5≠70。</div></div>'
            '<div class="flow-box"><b>辩护</b><div class="tiny">检查指控是否成立。能反驳就写清理由；反驳不了，就承认这一段站不住。</div></div>'
            '<div class="flow-box ok"><b>仲裁</b><div class="tiny">听完两边，给出过程是否成立、最早错步。它的意见很重要，但仍可能被符号证据或答案规则盖过。</div></div>',
        ),
        (
            "R1 · 第 4 段",
            "汇总按固定顺序",
            "到这里不再问模型。按下面的优先级把前面几段的产出收成一条结论。",
            _r1_pills(4)
            + '<div class="flow-box"><b>1</b> 符号检查已经证伪某一步 → 以这一步为最早错误。<br>'
            "<b>2</b> 否则看仲裁：它给出了明确步号，就采用。<br>"
            "<b>3</b> 指控提出了步号、辩护没有反驳成功 → 采用指控。<br>"
            "<b>4</b> 再退回逐段审查自己标出的第一个 INVALID。<br>"
            "<b>5</b> 答案已经对不上 → 禁止再把过程说成成立。</div>"
            '<p class="slide-p">矩形面积那道题走第 1 条：12×5≠70 已经把第 2 步确定下来。'
            "第 5 条是开关，和「指出第几步」分开记录。</p>",
        ),
        (
            "应用",
            "应用里怎么查看",
            "打开「解题与审计」，选 R1 和演示案例，就能看到下面这样的结果，不必调用接口。",
            '<div class="kv">'
            '<div class="flow-box"><b>解题与审计</b><div class="tiny">选题目，看独立求解、逐段标记、对质和汇总。</div></div>'
            '<div class="flow-box"><b>评测看板</b><div class="tiny">公开集和私有集的数字、柱状图。</div></div>'
            '<div class="flow-box"><b>错误探索</b><div class="tiny">按来源和错误类型翻原始样本。</div></div>'
            '<div class="flow-box"><b>演示分镜</b><div class="tiny">当前这一套说明页，也可单独翻看。</div></div>'
            "</div>"
            '<p class="slide-p">接下来三页是应用里的三道例题：过程成立、中间算错、答案对但过程不完整。</p>',
        ),
        (
            "应用 · 例题 1",
            "过程成立的例子",
            "割草机两种模式：整块草坪 Turtle 60 分钟、Rabbit 40 分钟。今天各用一半，一共多少分钟？",
            '<div class="app-frame"><div class="app-bar">解题与审计 · R1 反思式审查 · 演示案例</div>'
            '<div class="app-q">一半 Turtle、一半 Rabbit。参考答案 50 分钟。</div>'
            + _app_metrics("50", True, True, "—")
            + '<div class="flow-box ok"><b>独立求解</b> 同样得到 50。两边一致，不对质。</div>'
            '<div class="flow-box ok"><b>Step 1–5</b> 全部 VALID：60/2=30，40/2=20，30+20=50。</div>'
            '<div class="tiny">每一步都有题设支撑，没有跳步。应用里会把五段都标成成立。</div></div>',
        ),
        (
            "应用 · 例题 2",
            "中间一步算错",
            "长方形长 12、宽 5，面积应是 60。学生写成 70。应用里会标出第 2 步。最后一步只是把错的数抄下去。",
            '<div class="app-frame"><div class="app-bar">解题与审计 · R1 反思式审查 · 演示案例</div>'
            '<div class="app-q">一个长方形长 12、宽 5。它的面积是多少？</div>'
            + _app_metrics("70", False, False, "Step 2")
            + '<div class="flow-box ok"><b>Step 1</b> VALID · 面积 = 长 × 宽</div>'
            '<div class="flow-box bad"><b>Step 2</b> INVALID · 最早错误 · 计算错误 · <code>12×5=70</code>，应为 60</div>'
            '<div class="flow-box warn"><b>Step 3</b> 跟着错 · 「因此面积为 70」只是把错的数抄下去</div>'
            '<div class="tiny">独立求解得到 60，两边对不上，打开指控。反例 12×5≠70，辩护无法反驳。</div></div>',
        ),
        (
            "应用 · 例题 3",
            "答案对了，过程不完整",
            "题目要与 v=(3,−4) 共线的非零向量。学生写成 (3λ,−4λ)，数字能对上，但没排除 λ=0。",
            '<div class="app-frame"><div class="app-bar">解题与审计 · R1 反思式审查 · 演示案例</div>'
            '<div class="app-q">已知向量 v = (3, −4)。写出所有与 v 共线的非零向量的一般形式。</div>'
            + _app_metrics("(3λ, −4λ)", True, False, "Step 3")
            + '<div class="flow-box warn"><b>答案对、过程撑不住</b> 参考答案也是这个形式，但过程漏了 λ≠0。</div>'
            '<div class="flow-box ok"><b>Step 1–2</b> VALID · 共线向量写成数乘，代入得到 (3k,−4k)。</div>'
            '<div class="flow-box bad"><b>Step 3</b> INVALID · λ 取 0 时得到零向量，题目要求非零。</div></div>',
        ),
        (
            "公开评测",
            "题越难，指出首错越吃力",
            "B0 一次判断，数字由原始记录重算。发现有错仍然高，指出最早那一步则随难度往下走。",
            _svg_pb_line()
            + '<p class="slide-p">GSM8K 到 Olympiad，指出首错从 0.84 降到 0.69。'
            "发现「这份解答有问题」相对容易；把步号确定下来，在竞赛题上更难。</p>",
        ),
        (
            "公开评测",
            "各数据集对照",
            "三集合计 n=244：发现有错 0.98，指出首错 0.78，放过正确过程 0.87。公开主数字来自 B0。",
            '<table class="cmp"><tr><th>数据集</th><th>发现有错</th><th>指出最早错步</th><th>放过正确过程</th><th>n</th></tr>'
            "<tr><td>GSM8K</td><td>1.00</td><td>0.84</td><td>1.00</td><td>36</td></tr>"
            "<tr><td>MATH</td><td>1.00</td><td>0.81</td><td>0.88</td><td>103</td></tr>"
            "<tr><td>Omni-MATH</td><td>0.95</td><td>0.75</td><td>0.77</td><td>105</td></tr>"
            "<tr><td>OlympiadBench</td><td>0.91</td><td>0.69</td><td>0.89</td><td>105</td></tr>"
            "<tr><td>三集合计</td><td>0.98</td><td>0.78</td><td>0.87</td><td>244</td></tr>"
            "</table>"
            '<p class="slide-p" style="margin-top:10px">R1 还没有在 ProcessBench 上跑过。下面私有高中集上的 R1，不能直接套到这张表。</p>',
        ),
        (
            "私有数据",
            "私有高中题，只在本地使用",
            "约 4300 道高中选择/填空，带官方详解和模型逐步解答。不公开、不进远程仓库。",
            '<p class="slide-p">这批数据没有人工标注「哪一步开始错」。冻结了 88 道（seed 42）做对照，按来源拆开看。</p>'
            '<table class="cmp"><tr><th>子集</th><th>条数</th><th>能看什么</th></tr>'
            "<tr><td>模型答案已经算错</td><td>28</td><td>能不能发现过程有问题</td></tr>"
            "<tr><td>模型答案算对了</td><td>28</td><td>会不会把对的过程判错</td></tr>"
            "<tr><td>官方详解</td><td>16</td><td>会不会把教材步骤判不成立</td></tr>"
            "<tr><td>在官方步骤上改错</td><td>16</td><td>能不能指到被改的那一步</td></tr>"
            "</table>",
        ),
        (
            "私有数据",
            "同一 88 道题上的对照",
            "审查模型都是 Hy3。R1 更会抓「答案已经错了」和「形式没收齐」，对官方详解更严。",
            _hs_bars()
            + '<p class="slide-p">左起第一柱：B0 抓住 4/28，R1 抓住 28/28。'
            "第二柱步号对上从 11/16 到 12/16。第三柱官方详解被接受从 7/16 降到 6/16。"
            "右边两项的调和平均：B0 0.54，R1 0.50。</p>",
        ),
        (
            "私有数据",
            "四项对照",
            "R1 在「抓住答案错」上很高，在「放过详解」上更低。综合结果没有高于 B0。",
            '<div class="two">'
            + _svg_radar()
            + '<div>'
            '<div class="flow-box">四项画在同一尺度上。某一项到 1.00，另外一项掉下去，综合结果不一定更好。</div>'
            '<div class="flow-box warn">「抓住答案错」主要靠答案规则，逐步审查自己标错大约 0.18。</div>'
            '<div class="flow-box">改错样本上的步号更接近定位能力。这里 R1 略好于 B0。</div>'
            "</div></div>",
        ),
        (
            "私有数据",
            "28 道是怎么判出来的",
            "最终答案已经和参考答案对不上。R1 规定这种情况不许再把过程说成成立，所以 28 道全部判有问题。",
            _hs_gate()
            + '<p class="slide-p">逐步审查自己标出 INVALID 的大约 5 道；大约 18 道逐步仍认为每步都对，是答案规则把它改过来的。'
            "1.00 这个检出率，主要来自这条规则，逐步自己找到错步的比例大约 0.18。</p>",
        ),
        (
            "怎么读",
            "这些数字分别在说什么",
            "同一套框架，不同数字讲的是不同能力。混在一起报，会把规则补上的检出说成定位能力。",
            '<div class="flow-box"><b>发现过程有错</b> 审查器判了「不成立」。在答案已经错的子集上，一条规则就能把这项拉到 1.00。</div>'
            '<div class="flow-box"><b>指出最早错步</b> 只有改错样本能对步号。R1 12/16，里面多数来自逐段审查，只有 2 条靠答案规则改判。</div>'
            '<div class="flow-box"><b>放过正确过程</b> 官方详解当作大体正确。R1 更严，10/16 判了不成立，所以这项掉下来。</div>'
            '<div class="flow-box"><b>两项折中</b> 后两项的调和平均。R1 0.50，略低于 B0 0.54：抓错更多，把对的过程判错也更多。</div>'
            '<div class="kv">'
            '<div class="flow-box ok"><b>适合用来</b><div class="tiny">找失败模式、调整提示词、看规则有没有补得过严。</div></div>'
            '<div class="flow-box warn"><b>定位数字的范围</b><div class="tiny">私有集没有逐步人工标注，步号只能看改错这 16 道。</div></div>'
            "</div>",
        ),
        (
            "设计",
            "这套设计好在哪",
            "把找错拆成可以回看的几段。结论从规则里给出，不依赖单次生成的语气。",
            '<div class="kv">'
            '<div class="flow-box ok"><b>过程看得见</b><div class="tiny">独立结论、逐段标记、对质记录、汇总理由都可以打开，能顺着往回翻。</div></div>'
            '<div class="flow-box ok"><b>参考答案不进提示</b><div class="tiny">独立求解看不到学生步骤，审查提示也不写参考答案。答案只作为对错开关。</div></div>'
            '<div class="flow-box ok"><b>能算出来的错优先</b><div class="tiny">12×5≠70 这类证据优先于口头辩护，定位更稳。</div></div>'
            '<div class="flow-box ok"><b>首错和跟着错分开</b><div class="tiny">评测时对得上步号，讲解时也知道从哪一步开始。</div></div>'
            "</div>",
        ),
        (
            "设计",
            "目前的限制",
            "四段审查调用更多、更慢；高检出主要靠答案规则；对教材详解偏严。",
            '<div class="flow-box warn"><b>调用多</b> 独立求解、逐段、必要时三轮对质，一条样本可能打四五次模型。批量评测成本明显高于 B0。</div>'
            '<div class="flow-box warn"><b>检出偏高</b> 答案已经对不上时强制判过程不成立，检出率好看，定位能力几乎没被这项推高。</div>'
            '<div class="flow-box warn"><b>对详解偏严</b> 官方步骤常有跳步、口语化。R1 更容易打 INVALID，放过正确过程这项掉了。</div>'
            '<div class="flow-box warn"><b>UNKNOWN 容易进入对质</b> 说不清就打开对质，费用上去，结论却不一定更准。</div>'
            '<div class="flow-box warn"><b>私有集标不全</b> 没有逐步人工标注，就无法在这批题上报告「指出首错」的完整成绩。</div>',
        ),
        (
            "小结",
            "下一步",
            "公开集上一次判断已经能用。私有集上 R1 更会抓形式不完整，对详解更严，两项折中略低。",
            '<div class="flow-box">放松逐步和指控：少把教材跳步判成错误，让对的详解少被判不成立。</div>'
            '<div class="flow-box">「答案对不上」继续当开关，单独列表；和「指出第几步」分开写。</div>'
            '<div class="flow-box">形式不完整单独列一类：停在参数族、没按题目要求收束，过程就不成立。</div>'
            '<div class="flow-box ok">应用里继续把四段流程、首错和跟着错、公开集与私有集的图摊开给使用者看。</div>',
        ),
    ]
    idx = max(0, min(slide, len(slides) - 1))
    kicker, title, lead, body = slides[idx]
    _slide_shell(kicker, title, lead, body, f"{idx + 1} / {len(slides)}")


def main() -> None:
    pages = ["解题与审计", "评测看板", "错误探索", "演示分镜"]
    page_from_q = str(st.query_params.get("page", "")).lower()
    page_map = {
        "solve": "解题与审计",
        "dashboard": "评测看板",
        "explorer": "错误探索",
        "story": "演示分镜",
    }
    default_page = page_map.get(page_from_q, "解题与审计")
    try:
        slide = int(st.query_params.get("slide", 0))
    except (TypeError, ValueError):
        slide = 0
    with st.sidebar:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
            f'{LOGO_SVG}<div><div style="font-family:Source Serif 4,serif;font-size:20px;'
            f'font-weight:700;color:#1a5fb4;">MathXRay</div>'
            f'<div style="font-size:12px;color:#6b7280;">Hy3 数学推理过程审查</div></div></div>',
            unsafe_allow_html=True,
        )
        page = st.radio("页面", pages, index=pages.index(default_page))
        st.markdown("---")
        st.caption("独立求解 · 逐段审查 · 指控 / 辩护 / 仲裁 · 规则汇总")
    if page == "解题与审计":
        page_solve()
    elif page == "评测看板":
        page_dashboard()
    elif page == "演示分镜":
        page_story(slide)
    else:
        page_explorer()


if __name__ == "__main__":
    main()
