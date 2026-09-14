"""MathXRay Streamlit application — Solve & Audit / Dashboard / Error Explorer."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from src.analysis.reporting import latest_by_sample, load_jsonl
from src.config import ConfigError, load_config
from src.factory import build_hybrid, build_solver, generation_config
from src.pipeline import MathXRayPipeline
from src.taxonomy import ERROR_TYPE_LABELS

ROOT = Path(__file__).resolve().parent
DEMO_PATH = ROOT / "data" / "demo_cases.json"
OFFICIAL_DIR = ROOT / "reports" / "official"
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
</style>
""",
    unsafe_allow_html=True,
)


def _load_demo() -> list[dict]:
    if not DEMO_PATH.exists():
        return []
    return json.loads(DEMO_PATH.read_text(encoding="utf-8")).get("cases", [])


def _load_official() -> dict | None:
    path = OFFICIAL_DIR / "processbench_three_datasets.json"
    alt = OFFICIAL_DIR / "processbench_overall.json"
    for p in (path, alt):
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return None


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
    st.markdown(
        '<div class="mx-hero"><div class="mx-kicker">SOLVE &amp; AUDIT</div>'
        '<div class="mx-title">不只看答案，还要看推理是否成立</div>'
        '<div class="mx-sub">Hy3 负责解题；MathXRay 用符号验证 + 语义审查定位最早错误，'
        "并标出「答案碰巧正确」的样本。</div></div>",
        unsafe_allow_html=True,
    )
    cases = _load_demo()
    mode = st.radio(
        "输入方式",
        ["演示案例（推荐录屏）", "现场调用 Hy3"],
        horizontal=True,
    )

    if mode.startswith("演示"):
        labels = [f"{c['title']}" for c in cases]
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
    gold = st.text_input("标准答案（可选，用于自动校验）")
    if st.button("求解并审计", type="primary", disabled=not problem.strip()):
        try:
            config = load_config(ROOT / "configs" / "default.yaml")
            pipe = MathXRayPipeline(build_solver(config, "hy3"), build_hybrid(config, "hy3"))
            with st.spinner("Hy3 解题并审计中…"):
                result = pipe.run(problem.strip(), gold_answer=gold.strip() or None, gen_cfg=generation_config(config))
        except (ConfigError, SystemExit) as exc:
            st.error(f"无法调用 Hy3：{exc}。请配置 `.env` 中的 HY3_API_KEY / HY3_MODEL，或改用演示案例。")
            return
        except Exception as exc:  # noqa: BLE001
            st.error(f"运行失败：{exc}")
            return
        _render_live(result)


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
        st.info("建议人工复核（符号证据与语义审查不一致）。")
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


def page_dashboard() -> None:
    st.markdown(
        '<div class="mx-hero"><div class="mx-kicker">BENCHMARK DASHBOARD</div>'
        '<div class="mx-title">外部金标准上的过程评估结果</div>'
        "<div class=\"mx-sub\">三数据集切片 GSM8K + MATH + Omni-MATH。"
        "数字全部来自 `reports/official/`，由 raw JSONL 重算，不手填。</div></div>",
        unsafe_allow_html=True,
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

    full_path = OFFICIAL_DIR / "processbench_full_replay.json"
    if full_path.exists():
        full = json.loads(full_path.read_text(encoding="utf-8"))
        st.subheader("B0 vs Full（符号融合回放，无额外 API）")
        st.write(
            {
                "B0 M2": (full.get("B0") or {}).get("first_error_exact"),
                "Full M2": (full.get("Full") or {}).get("first_error_exact"),
                "Δ": full.get("delta_first_error_exact"),
                "n": full.get("n"),
            }
        )


def page_explorer() -> None:
    st.markdown(
        '<div class="mx-hero"><div class="mx-kicker">ERROR EXPLORER</div>'
        '<div class="mx-title">可追溯到每一条样本</div>'
        "<div class=\"mx-sub\">筛选来源、过程状态与错误类型。样本 ID 与 raw JSONL 对齐。</div></div>",
        unsafe_allow_html=True,
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


def main() -> None:
    pages = ["解题与审计", "评测看板", "错误探索"]
    page_from_q = str(st.query_params.get("page", "")).lower()
    page_map = {"solve": "解题与审计", "dashboard": "评测看板", "explorer": "错误探索"}
    default_page = page_map.get(page_from_q, "解题与审计")
    with st.sidebar:
        st.markdown("### MathXRay")
        st.caption("Hy3 数学推理过程评估")
        page = st.radio("页面", pages, index=pages.index(default_page))
        st.markdown("---")
        st.caption("Hy3 Solver + Semantic Critic\nSymPy 符号验证 + 依赖图")
    if page == "解题与审计":
        page_solve()
    elif page == "评测看板":
        page_dashboard()
    else:
        page_explorer()


if __name__ == "__main__":
    main()
