# MathXRay 分析报告

> 本报告数字来自 `reports/official/` 与 `reports/manual_audit.csv`，可由 raw JSONL 重算。

## 1. 动机

最终答案正确并不蕴含推理过程成立。课题 2 要求在可验证场景中同时给出：答案校验、过程是否成立、最早错误步骤、错误类型，以及「答案正确但过程无法支撑结论」的识别。MathXRay 选择数学推理，因为存在标准答案、可自动校验，以及 ProcessBench 这样的第三方过程金标准。

## 2. 任务定义

对每条显式解题轨迹输出：`final_answer_correct`、`process_correct`、`first_error_step`（1-based，全过程正确为 null）、`error_type`、`unsupported_answer`。

## 3. 方法

Hy3 承担两个角色：**Solver**（结构化 `solution_steps`）与 **Semantic Critic**（Direct Judge）。确定性 **SymPy 符号验证**优先于 LLM：一旦某步等式可证伪，即定为该步 INVALID。依赖图只解释 ROOT / PROPAGATED / INDEPENDENT，不改写外部 gold。R10 选择的是「规则 + 分步 LLM」，不是大规模多 Agent。

## 4. 错误分类

一级类别见 `docs/taxonomy.md`。传播标签独立于错误类型。ProcessBench 没有类型 gold，下表只报告**预测分布**。

| Type | 中文 | Count |
|---|---|---|
| CONCEPT_ERROR | 概念错误 | 53 |
| PROBLEM_MISREAD | 题意误读 | 28 |
| ARITHMETIC_ERROR | 计算错误 | 24 |
| ALGEBRA_ERROR | 代数变形错误 | 22 |
| CONDITION_OMISSION | 条件遗漏 | 18 |
| LOGIC_GAP | 逻辑跳步 | 13 |
| THEOREM_MISUSE | 定理误用 | 8 |
| HALLUCINATION | 幻觉/无中生有 | 4 |
| CIRCULAR_REASONING | 循环论证 | 1 |

## 5. ProcessBench 三数据集主结果（GSM8K + MATH + Omni-MATH）

| Metric | Value | 95% CI |
|---|---|---|
| M1 Error Detection Recall | 0.976 | 0.976 [0.952, 0.994] |
| M2 First-Error Exact | 0.782 | 0.782 [0.715, 0.842] |
| M3 Correct Process Accuracy | 0.873 | 0.873 [0.797, 0.937] |
| M4 Process Status Accuracy | 0.943 | — |
| M5 Official Composite | 0.811 | — |

n = 244，parse failure = 2，API failure = 0。

| Source | M1 | M2 Exact | M3 | M5 | n |
|---|---|---|---|---|---|
| gsm8k | 1.000 | 0.842 | 1.000 | 0.917 | 36 |
| math | 1.000 | 0.810 | 0.875 | 0.835 | 103 |
| omnimath | 0.952 | 0.747 | 0.773 | 0.752 | 105 |

能力边界：First-Error Exact 最大相邻降幅为 **D3 (math, 0.810) → D5 (omnimath, 0.747)**，降幅 0.063。

OlympiadBench 作为额外高难 split 写入 `processbench_overall.json`，不并入「三数据集」主表，以免与方案文档的 GSM8K/MATH/Omni-MATH 口径混淆。

## 6. B0 vs Full

在 ProcessBench 已跑样本上，用存储的 B0 语义预测与本地符号验证融合（无额外 API）： B0 M2 = 0.747， Full M2 = 0.722， Δ = -0.025，n = 300。

若 Δ 的区间穿过 0，只称为 observed difference，不称显著。

## 7. Unsupported answers

Gold A✓P✗ 样本 37 条；评估器召回 0.919。 A✓P✓ 上的过程问题标记率 0.127（这不是 classic FPR 的完整负类估计，除非集合穷尽）。

## 8. 人工抽检（R12）

在「最终答案正确且评估器标记过程有问题」的集合中抽检 n=14 （seed=42，见 `reports/manual_audit.csv`）。

| 标签 | n |
|---|---|
| REAL_PROCESS_ERROR | 1 |
| FALSE_POSITIVE | 12 |
| UNCERTAIN | 1 |

Real Issue Rate = 0.077；**Flagged-set False Discovery Proportion** = 0.923。 此处不报告 classic FPR（没有完整 gold 负类全集之外的 TN 计数约定之外的扩展）。

## 9. SolveBench 与 TraceAdversarialBench

构造与运行命令见 `data/README.md`。SolveBench 无过程 gold，只报告 Final Answer Accuracy、Unknown 率、按难度分层，以及 Process Issue Flag Rate（**不是** Process Accuracy）。当前冻结子集见 `data/processed/solvebench.manifest.json`；GSM8K（D1）若未能从 Hugging Face 载入，会在 manifest 中显示为 0，不得事后补抽。

TraceAdversarialBench **符号-only**（`--provider none`，无 Hy3 critic）n=80：M2 = 0.138，类型 Macro-F1 = 0.124，answer-preserving 召回 = 0.429 (n=21)。 该数字证明纯符号覆盖不足，因此主路径仍需要 Hy3 Semantic Critic；不得把符号-only 结果写成 Full 方法的正式分数。

## 10. 效率

B0 每样本 1 次 Hy3 调用。Full 在回放设置下 0 次额外调用（复用 B0 raw）。应用现场路径为 Solver 1 次 + Critic 1 次。符号验证为本地 CPU。

## 11. 失败模式

- 长链竞赛题上首错偏早（把不严谨的表述当成新错误）。
- 正确过程上的语义误报（FALSE_POSITIVE）。
- 空响应 / 非 JSON 导致 parse failure（已计入分母，不丢弃）。
- 符号覆盖率有限：无等式的纯叙述步骤保持 UNKNOWN。

## 12. 局限

正式 ProcessBench 主数字来自 Direct Judge 分层子集（非全量 3400）。SolveBench 若因 API 配额未能跑满注册集，以 `data/processed/solvebench.manifest.json` 为准披露。不把 Hy3 对自身解答的判定当作过程 gold。
