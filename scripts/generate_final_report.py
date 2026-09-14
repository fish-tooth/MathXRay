"""Render reports/final_report.md from frozen official JSON + audit CSV."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from src.taxonomy import ERROR_TYPE_LABELS


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def _audit_stats(path: Path) -> dict:
    if not path.exists():
        return {}
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    flagged = [
        r
        for r in rows
        if r.get("gold_final_answer_correct") == "True"
        and r.get("evaluator_flags_process_issue") == "True"
    ]
    real = sum(1 for r in flagged if r.get("human_label") == "REAL_PROCESS_ERROR")
    fp = sum(1 for r in flagged if r.get("human_label") == "FALSE_POSITIVE")
    unc = sum(1 for r in flagged if r.get("human_label") == "UNCERTAIN")
    den = real + fp
    return {
        "n_flagged_reviewed": len(flagged),
        "real": real,
        "fp": fp,
        "uncertain": unc,
        "real_issue_rate": (real / den) if den else None,
        "fdp": (fp / den) if den else None,
    }


def main() -> int:
    official = Path("reports/official")
    three = _load(official / "processbench_three_datasets.json")
    overall = _load(official / "processbench_overall.json")
    full = _load(official / "processbench_full_replay.json")
    audit = _audit_stats(Path("reports/manual_audit.csv"))
    m = three.get("metrics") or overall.get("metrics") or {}
    ci = three.get("ci") or overall.get("ci") or {}
    per = three.get("per_source") or overall.get("per_source") or {}
    dist = three.get("error_type_distribution") or overall.get("error_type_distribution") or {}
    uns = three.get("unsupported") or overall.get("unsupported") or {}
    bound = three.get("capability_boundary") or overall.get("capability_boundary") or {}

    lines = []
    lines.append("# MathXRay 分析报告")
    lines.append("")
    lines.append("> 本报告数字来自 `reports/official/` 与 `reports/manual_audit.csv`，可由 raw JSONL 重算。")
    lines.append("")
    lines.append("## 1. 动机")
    lines.append("")
    lines.append("最终答案正确并不蕴含推理过程成立。课题 2 要求在可验证场景中同时给出：答案校验、过程是否成立、最早错误步骤、错误类型，以及「答案正确但过程无法支撑结论」的识别。MathXRay 选择数学推理，因为存在标准答案、可自动校验，以及 ProcessBench 这样的第三方过程金标准。")
    lines.append("")
    lines.append("## 2. 任务定义")
    lines.append("")
    lines.append("对每条显式解题轨迹输出：`final_answer_correct`、`process_correct`、`first_error_step`（1-based，全过程正确为 null）、`error_type`、`unsupported_answer`。")
    lines.append("")
    lines.append("## 3. 方法")
    lines.append("")
    lines.append("Hy3 承担两个角色：**Solver**（结构化 `solution_steps`）与 **Semantic Critic**（Direct Judge）。确定性 **SymPy 符号验证**优先于 LLM：一旦某步等式可证伪，即定为该步 INVALID。依赖图只解释 ROOT / PROPAGATED / INDEPENDENT，不改写外部 gold。R10 选择的是「规则 + 分步 LLM」，不是大规模多 Agent。")
    lines.append("")
    lines.append("## 4. 错误分类")
    lines.append("")
    lines.append("一级类别见 `docs/taxonomy.md`。传播标签独立于错误类型。ProcessBench 没有类型 gold，下表只报告**预测分布**。")
    lines.append("")
    lines.append("| Type | 中文 | Count |")
    lines.append("|---|---|---|")
    for k, v in sorted(dist.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {k} | {ERROR_TYPE_LABELS.get(k, k)} | {v} |")
    lines.append("")
    lines.append("## 5. ProcessBench 三数据集主结果（GSM8K + MATH + Omni-MATH）")
    lines.append("")
    lines.append("| Metric | Value | 95% CI |")
    lines.append("|---|---|---|")
    for key, label in [
        ("error_detection_recall", "M1 Error Detection Recall"),
        ("first_error_exact", "M2 First-Error Exact"),
        ("correct_process_accuracy", "M3 Correct Process Accuracy"),
        ("process_status_accuracy", "M4 Process Status Accuracy"),
        ("official_composite", "M5 Official Composite"),
    ]:
        extra = (ci.get(key) or {}).get("fmt") or "—"
        lines.append(f"| {label} | {_fmt(m.get(key))} | {extra} |")
    lines.append("")
    lines.append(f"n = {m.get('n_all', three.get('n') or overall.get('n'))}，parse failure = {m.get('n_parse_failure')}，API failure = {m.get('n_api_failure')}。")
    lines.append("")
    lines.append("| Source | M1 | M2 Exact | M3 | M5 | n |")
    lines.append("|---|---|---|---|---|---|")
    for src, row in sorted(per.items()):
        lines.append(
            f"| {src} | {_fmt(row.get('error_detection_recall'))} | {_fmt(row.get('first_error_exact'))} | "
            f"{_fmt(row.get('correct_process_accuracy'))} | {_fmt(row.get('official_composite'))} | {row.get('n_all')} |"
        )
    lines.append("")
    if bound:
        lines.append(
            f"能力边界：First-Error Exact 最大相邻降幅为 **{bound.get('from_difficulty')} "
            f"({bound.get('from')}, {_fmt(bound.get('from_value'))}) → "
            f"{bound.get('to_difficulty')} ({bound.get('to')}, {_fmt(bound.get('to_value'))})**，"
            f"降幅 {_fmt(bound.get('drop'))}。"
        )
        lines.append("")
    lines.append("OlympiadBench 作为额外高难 split 写入 `processbench_overall.json`，不并入「三数据集」主表，以免与方案文档的 GSM8K/MATH/Omni-MATH 口径混淆。")
    lines.append("")
    lines.append("## 6. B0 vs Full")
    lines.append("")
    if full:
        lines.append(
            f"在 ProcessBench 已跑样本上，用存储的 B0 语义预测与本地符号验证融合（无额外 API）："
            f" B0 M2 = {_fmt((full.get('B0') or {}).get('first_error_exact'))}，"
            f" Full M2 = {_fmt((full.get('Full') or {}).get('first_error_exact'))}，"
            f" Δ = {_fmt(full.get('delta_first_error_exact'))}，n = {full.get('n')}。"
        )
        lines.append("")
        lines.append("若 Δ 的区间穿过 0，只称为 observed difference，不称显著。")
    else:
        lines.append("尚未生成 `processbench_full_replay.json`。运行 `python scripts/replay_full_hybrid.py`。")
    lines.append("")
    lines.append("## 7. Unsupported answers")
    lines.append("")
    lines.append(
        f"Gold A✓P✗ 样本 {uns.get('n_unsupported_answer')} 条；"
        f"评估器召回 {_fmt(uns.get('unsupported_recall'))}。"
        f" A✓P✓ 上的过程问题标记率 {_fmt(uns.get('flag_rate_on_supported_correct'))}（这不是 classic FPR 的完整负类估计，除非集合穷尽）。"
    )
    lines.append("")
    lines.append("## 8. 人工抽检（R12）")
    lines.append("")
    if audit:
        lines.append(
            f"在「最终答案正确且评估器标记过程有问题」的集合中抽检 n={audit.get('n_flagged_reviewed')} "
            f"（seed=42，见 `reports/manual_audit.csv`）。"
        )
        lines.append("")
        lines.append("| 标签 | n |")
        lines.append("|---|---|")
        lines.append(f"| REAL_PROCESS_ERROR | {audit.get('real')} |")
        lines.append(f"| FALSE_POSITIVE | {audit.get('fp')} |")
        lines.append(f"| UNCERTAIN | {audit.get('uncertain')} |")
        lines.append("")
        lines.append(
            f"Real Issue Rate = {_fmt(audit.get('real_issue_rate'))}；"
            f"**Flagged-set False Discovery Proportion** = {_fmt(audit.get('fdp'))}。"
            " 此处不报告 classic FPR（没有完整 gold 负类全集之外的 TN 计数约定之外的扩展）。"
        )
    lines.append("")
    adv = _load(Path("reports/official/adversarial.json"))
    lines.append("## 9. SolveBench 与 TraceAdversarialBench")
    lines.append("")
    lines.append(
        "构造与运行命令见 `data/README.md`。SolveBench 无过程 gold，只报告 Final Answer Accuracy、"
        "Unknown 率、按难度分层，以及 Process Issue Flag Rate（**不是** Process Accuracy）。"
        "当前冻结子集见 `data/processed/solvebench.manifest.json`；GSM8K（D1）若未能从 Hugging Face 载入，"
        "会在 manifest 中显示为 0，不得事后补抽。"
    )
    lines.append("")
    if adv:
        lines.append(
            f"TraceAdversarialBench **符号-only**（`--provider none`，无 Hy3 critic）n={adv.get('n')}："
            f"M2 = {_fmt((adv.get('metrics') or {}).get('first_error_exact'))}，"
            f"类型 Macro-F1 = {_fmt(adv.get('error_type_macro_f1'))}，"
            f"answer-preserving 召回 = {_fmt(adv.get('unsupported_recall'))} "
            f"(n={adv.get('n_answer_preserving')})。"
            " 该数字证明纯符号覆盖不足，因此主路径仍需要 Hy3 Semantic Critic；"
            "不得把符号-only 结果写成 Full 方法的正式分数。"
        )
        lines.append("")
    else:
        lines.append(
            "尚未生成 `reports/official/adversarial.json`。"
            "运行 `python scripts/build_adversarial.py` 与 "
            "`python scripts/run_adversarial.py --provider none --method Full`。"
        )
        lines.append("")
    lines.append("## 10. 效率")
    lines.append("")
    lines.append("B0 每样本 1 次 Hy3 调用。Full 在回放设置下 0 次额外调用（复用 B0 raw）。应用现场路径为 Solver 1 次 + Critic 1 次。符号验证为本地 CPU。")
    lines.append("")
    lines.append("## 11. 失败模式")
    lines.append("")
    lines.append("- 长链竞赛题上首错偏早（把不严谨的表述当成新错误）。")
    lines.append("- 正确过程上的语义误报（FALSE_POSITIVE）。")
    lines.append("- 空响应 / 非 JSON 导致 parse failure（已计入分母，不丢弃）。")
    lines.append("- 符号覆盖率有限：无等式的纯叙述步骤保持 UNKNOWN。")
    lines.append("")
    lines.append("## 12. 局限")
    lines.append("")
    lines.append("正式 ProcessBench 主数字来自 Direct Judge 分层子集（非全量 3400）。SolveBench 若因 API 配额未能跑满注册集，以 `data/processed/solvebench.manifest.json` 为准披露。不把 Hy3 对自身解答的判定当作过程 gold。")
    lines.append("")

    out = Path("reports/final_report.md")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[report] {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
