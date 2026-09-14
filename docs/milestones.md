# MathXRay Milestones

> **Status:** Award-Ready Execution Plan v2.0  
> **Time baseline:** 单人约 3 周  
> **Management principle:** **先 benchmark，后创新；先真实结果，后 UI；先冻结口径，再跑正式 test。**  
> **Primary outcome:** 在有限时间内完成官方闭环，并形成“外部 benchmark + 可控 benchmark + 人工审计 + 消融 + 能力边界”的获奖级证据链。

---

# 1. 总体执行策略

项目不按“写完多少模块”推进，而按四个 Gate 推进：

## Gate G0 — Scope Ready

- requirements / evaluation / milestones 冻结；
- 官方要求全部映射；
- 指标口径无冲突；
- 项目目录、run metadata、data manifest 方案明确。

## Gate G1 — Baseline Real

必须出现第一张**真实 ProcessBench baseline 表**。

如果 G1 未通过：

> 禁止把主要时间投入 Streamlit 美化、复杂多 Agent 或报告包装。

## Gate G2 — Method Proven

至少一个核心模块在预注册指标或关键子集上证明有价值：

- First-Error Exact 提升；
- 或 Correct Process 误报下降；
- 或 Unsupported Answer 能力显著增强；
- 或效率/失败率明显改善。

如果没有任何证据：

> 简化/修正 evaluator，而不是强行把所有设计保留为“创新”。

## Gate G3 — Evidence Frozen

正式 test、人工 audit、难度分析、消融和结果文件全部冻结，可从 raw 重算。

## Gate G4 — Competition Ready

- clean clone 可运行；
- README 首屏有核心结果；
- Demo <120s；
- 评委 2 分钟内能理解价值；
- 所有 claim 有证据。

---

# 2. 优先级

## P0 — 官方闭环

最高优先：

1. Hy3 应用；
2. 完整显式步骤；
3. 标准答案与自动校验；
4. 过程正确性；
5. earliest error；
6. error taxonomy；
7. final-correct/process-invalid；
8. 定位准确率；
9. 误报人工抽检；
10. 难度分析；
11. 完整交付物。

## P1 — 竞赛壁垒

1. ProcessBench external gold；
2. Direct Hy3 baseline；
3. Symbolic deterministic evidence；
4. Dependency/root propagation；
5. TraceAdversarialBench；
6. ablation；
7. bootstrap CI；
8. reproducibility；
9. efficiency；
10. error explorer。

## P2 — Stretch

- calibration；
- second reviewer；
- semantic mutations；
- richer dashboard；
- Pareto analysis。

---

# 3. 三周关键路径总览

| 阶段 | 时间 | 核心目标 | Gate |
|---|---|---|---|
| **Phase 0** | Day 0–1 | 文档冻结 + repo/实验地基 | G0 |
| **Phase 1** | Day 1–5 | Hy3 主链路 + ProcessBench Direct baseline | G1 |
| **Phase 2** | Day 6–12 | Symbolic + Dependency + Adversarial + 初版消融 | G2 |
| **Phase 3** | Day 13–17 | Freeze + 正式评测 + 人工 audit + 难度 | G3 |
| **Phase 4** | Day 18–21 | UI/README/报告/Demo/clean-room 验收 | G4 |

> 时间不足时：先缩 UI 和 P2，不削减 P0、external baseline、manual audit、raw reproducibility。

---

# 4. Phase 0 — Day 0–1：冻结需求与实验地基

# M0 — Project Governance Freeze

## 目标

确保后续 CodeBuddy/人工开发只围绕唯一规范执行，避免 requirements、指标、目录反复漂移。

## 输入

- `docs/requirements.md`
- `docs/evaluation_protocol.md`
- `docs/milestones.md`
- 方案文档

## 工作

- 建立 repo；
- 将三份 docs 提交为 baseline commit；
- 建立 `CHANGELOG/DECISIONS`；
- 确认 R1–R20 追踪；
- 确认 P0/P1/P2；
- 确认 canonical step id / no-error 表示；
- 确认正式 run metadata schema。

## 产物

- initial commit；
- docs；
- README skeleton；
- `configs/default.yaml` skeleton；
- `.env.example` skeleton。

## 退出标准

- [ ] 官方要求全部有验收入口
- [ ] R10 明确为 ALLOW，不被误解为“必须多 Agent”
- [ ] Hy3 repo 链接不再算“R21 官方要求”
- [ ] FPR/FDP 口径冻结
- [ ] internal first-error index 冻结
- [ ] 新 feature 必须关联 Requirement ID

---

# M1 — Repository & Reproducibility Scaffold

## 目标

在第一行模型代码前先保证实验不会“跑完但无法追溯”。

## 范围

- package layout；
- `pyproject.toml`；
- config；
- logging；
- run id；
- raw/parsed/result 目录；
- cache interface；
- mock provider；
- pytest skeleton。

## 退出标准

- [ ] `pytest` skeleton 可运行
- [ ] git commit 可写入 run metadata
- [ ] API key 只来自 env
- [ ] raw output 与 summary 分目录
- [ ] cache key 设计包含 model/prompt/config/input
- [ ] resume 设计有唯一 run signature

---

# 5. Phase 1 — Day 1–5：先拿到真实 baseline

# M2 — Hy3 Provider

## 目标

证明最终独立应用真正调用 Hy3。

## 范围

- OpenAI-compatible provider；
- timeout；
- retry；
- cache；
- metadata；
- mock provider；
- cloud/local endpoint config。

## 退出标准

- [ ] 实际 Hy3 请求成功
- [ ] mock 测试不消耗真实 API
- [ ] API failure 有明确错误
- [ ] retry 不重复写入结果
- [ ] model/config 写入 metadata

## 对应

R1、R4、R15、EXT-08、EXT-12

---

# M3 — Structured / Auditable Solver

## 目标

让 Hy3 输出可被 evaluator 逐步引用的外部审计步骤。

## 范围

- problem；
- atomic `solution_steps`；
- final answer；
- schema validation；
- parser fallback；
- prompt versioning。

## 退出标准

- [ ] 20–30 条 smoke 输出格式稳定
- [ ] step id 连续且唯一
- [ ] final answer 字段独立
- [ ] parse failure 被记录
- [ ] 不要求/展示 hidden chain-of-thought

## 对应

R1、R4

---

# M4 — Answer Verifier

## 目标

尽早完成官方“明确标准答案 + 可自动校验”。

## 优先覆盖

1. normalized exact；
2. integer/float；
3. fraction/percentage；
4. SymPy equivalence；
5. roots/set；
6. UNKNOWN。

## 测试策略

**tests first**：

- equivalent；
- non-equivalent；
- malformed；
- ambiguous；
- parser failure。

## 退出标准

- [ ] 至少 50 个 verifier unit cases
- [ ] UNKNOWN 是合法结果
- [ ] 不把 parse failure 默认当错
- [ ] pilot 与人工检查一致性可接受
- [ ] 正式 SolveBench 样本均可分配 verification strategy

## 对应

R5.1、R5.2、R13

---

# M5 — ProcessBench Preflight & Adapter

## 目标

在任何“首错提升”实验前消灭最危险的 off-by-one / label 语义错误。

## 必须确认

- 实际 dataset schema；
- correct process label；
- first-error label；
- step numbering；
- split；
- final-answer correctness metadata（若有）；
- 官方 metric。

## 强制人工检查

至少 20 条：

- correct process；
- first step error；
- middle error；
- last error；
- 各主要 split。

## 退出标准

- [ ] canonical adapter tests 通过
- [ ] no-error → null 转换正确
- [ ] 1-based UI / canonical step id 一致
- [ ] 20 条人工检查记录留档
- [ ] 不能只凭历史文档假设 schema

## 对应

R11、EXT-02

---

# M6 — B0 Direct Hy3 Judge Baseline

## 目标

获得第一个可比较基线。

## 运行梯度

### Smoke

20–30 条。

### Pilot

50–100 条分层样本。

### Development baseline

200–400 条，按预算决定。

正式 full baseline 留到 Freeze 后。

## 输出

- raw JSONL；
- parsed JSONL；
- Error Detection；
- First-Error Exact；
- Correct Process Accuracy；
- failure count；
- latency。

## G1 退出标准

- [ ] 第一张真实 baseline 表已生成
- [ ] raw → metric 可重算
- [ ] 至少人工核对 20 条 pred/gold
- [ ] 主要失败模式已整理
- [ ] baseline prompt/version 已固定并保存

**未通过 G1：停止 UI 美化。**

---

# 6. Phase 2 — Day 6–12：建立核心竞争壁垒

# M7 — Baseline Failure Diagnosis

## 目标

创新来自 baseline 失败，而不是拍脑袋加模块。

## 分析

将失败至少按以下维度切分：

- arithmetic/algebra；
- semantic theorem/condition；
- early vs late step；
- correct-chain false positive；
- long chain；
- high difficulty；
- parse/format。

## 输出

`reports/baseline_diagnosis.md`、`reports/manual_audit.csv`、`reports/official/`

## 退出标准

- [ ] 每个计划新增模块对应至少一个观察失败模式
- [ ] 每个模块写出可证伪假设
- [ ] 不做与 baseline 问题无关的大架构扩张

---

# M8 — Symbolic Verifier V1

## 假设

高精度 deterministic evidence 能：

- 改善 arithmetic/algebra first-error；
- 或降低 LLM 对简单可验证步骤的误判。

## 首版范围

- arithmetic；
- equality；
- substitution；
- basic algebra。

## 状态

- VALID
- INVALID
- UNKNOWN

## 退出标准

- [ ] unit tests
- [ ] coverage 可统计
- [ ] INVALID precision sanity check
- [ ] UNKNOWN 不阻塞 pipeline
- [ ] 在 dev/pilot 完成 B0 vs +Symbolic

## Go / No-Go

如果无收益：

- 查 coverage；
- 查 parser；
- 查 fusion；
- 若仍无价值，降级为辅助 evidence，不作为核心 contribution。

---

# M9 — Dependency Graph / Root-Cause

## 假设

区分 root 与 propagated 能降低“把后续污染步骤误判为首错”的问题。

## 输出

- dependencies；
- ROOT；
- PROPAGATED；
- INDEPENDENT；
- `first_root_error`；
- support relation。

## 测试

构造：

- one root → many propagated；
- two independent errors；
- no error；
- dependency uncertainty。

## 退出标准

- [ ] root/propagation tests 通过
- [ ] 至少 3 个真实 dev case 显示机制价值
- [ ] 不修改外部 benchmark gold
- [ ] 完成 +Symbolic vs +Dependency pilot

---

# M10 — Conflict Arbitration

## 目标

只在真正 disagreement 时增加 Hy3 推理成本。

## 触发

例如：

- Symbolic VALID vs Semantic INVALID；
- Semantic 与 Consistency 冲突；
- low-confidence critical step。

## 退出标准

- [ ] arbitration rate 可统计
- [ ] 不无条件二次 Judge
- [ ] evidence 被明确传给 Arbiter
- [ ] arbiter failure 可回退 low confidence
- [ ] 额外 latency/call count 可报告

---

# M11 — TraceAdversarialBench V1

## 目标

得到 first-error/type/unsupported 的可控 gold。

## Day 6–10 首版只做 Tier A

- arithmetic
- sign
- operator
- numeric/denominator
- substitution
- answer-preserving

## 强制规则

- source trace 必须先验证正确；
- mutation step 可程序确定；
- mutation 后必须验证该 step 真错误；
- 保存 source/mutation/version/seed；
- dev/test 分离。

## 规模

先：

- dev 100–200

再：

- test 400–600（目标）

## 退出标准

- [ ] deterministic gold 可重建
- [ ] First-Error Exact 可算
- [ ] Type Metric 可算
- [ ] answer-preserving subset 可算 Unsupported Recall
- [ ] 至少抽查 30 条 mutation 质量

---

# M12 — Development Ablation

## 方法

- B0 Direct
- A2 + Symbolic
- A3 + Dependency
- A4 + Arbitration
- Full

A1 Structured schema 仅在公平适用的数据上比较。

## 目标

判断哪些模块值得进入最终故事。

## G2 退出标准

至少满足：

- [ ] Full 在主指标有稳定正向观察；
- [ ] 或某关键子集有明确提升；
- [ ] 或 correct-process false positive 明显改善；
- [ ] unsupported capability 明确优于 B0；
- [ ] 至少一个“模块 → 指标/案例”因果故事成立。

如果都不成立：

> Day 12 前优先修方法，不进入大量 UI 工作。

---

# 7. Phase 3 — Day 13–17：Freeze 与正式证据

# M13 — Taxonomy / Prompt / Config Freeze

## 冻结

- solver prompt；
- critic prompt；
- arbiter prompt；
- taxonomy；
- fusion；
- metrics；
- ProcessBench adapter；
- mutation rules；
- formal sample manifests；
- model settings。

## 输出

`formal_eval.yaml` + commit/tag。

## 退出标准

- [ ] prompt hash
- [ ] config hash
- [ ] dataset manifest hash
- [ ] git commit
- [ ] 不再用 formal test 调 prompt

---

# M14 — Formal ProcessBench Evaluation

## 成本策略

不要在开发期间重复 full 3,400 多次。

正式冻结后：

1. B0 full；
2. Full full；
3. 关键 ablation full 或预注册代表性 subset（按预算）；
4. paired bootstrap。

## 输出

主表：

- Error Detection
- First-Error Exact
- Correct Process Accuracy
- official composite
- CI
- Δ Full-B0
- failures
- efficiency

## 退出标准

- [ ] formal raw outputs 完整
- [ ] 95% CI
- [ ] paired comparison
- [ ] failure accounting
- [ ] result manifest
- [ ] 表中数字可由脚本重算

---

# M15 — SolveBench Formal Run + Difficulty

## 目标

完成官方 Final Answer Accuracy 与难度能力边界。

## 工作

- 冻结 D1–D5；
- 运行 SolveBench；
- answer verify；
- 收集 process flags；
- 分层统计；
- 最大相邻降幅；
- 条件允许 bootstrap CI。

## 退出标准

- [ ] Final Answer Accuracy
- [ ] 每层 N
- [ ] 分层 Final Acc
- [ ] 无过程 gold 时不写 Process Accuracy
- [ ] 明确 capability boundary 或诚实写“数据不足”

---

# M16 — TraceAdversarialBench Formal Test

## 目标

完成细粒度核心卖点：

- First Error
- Type
- Unsupported Answer

## 退出标准

- [ ] dev/test 隔离
- [ ] First-Error Exact
- [ ] Error-Type Macro-F1
- [ ] Unsupported Recall
- [ ] B0 vs Full
- [ ] 结果含 CI（至少主指标）

---

# M17 — Manual Audit

## Candidate Pool

`Final Answer Correct`
且
`Evaluator Flags Process Issue`

## 正式抽样

- 目标 n=100；
- 不足则全审；
- seed 固定；
- 保留 source/difficulty coverage。

## 人工字段

- real process issue；
- false positive；
- uncertain；
- first error；
- type；
- notes。

## Award Stretch

- 第二 reviewer ≥30 条；
- blind to method if feasible；
- agreement / κ。

## 退出标准

- [ ] `manual_audit.csv`
- [ ] candidate manifest
- [ ] Real Issue Rate
- [ ] False Discovery Proportion
- [ ] classic FPR 只有有完整 gold 时才报告
- [ ] 至少 3 个 false-positive failure cases

---

# M18 — G3 Evidence Freeze

## 目标

在写最终故事前锁死所有数字。

## 检查

- raw；
- parsed；
- summary；
- CI；
- audit；
- data manifest；
- figures；
- failure log；
- efficiency。

## G3 退出标准

- [ ] 主结果表完成
- [ ] 消融表完成
- [ ] difficulty 表完成
- [ ] error distribution 完成
- [ ] audit 表完成
- [ ] unsupported 结果完成
- [ ] 所有数字来自 frozen results
- [ ] 后续 UI/README 不允许手填与结果文件不一致的数字

---

# 8. Phase 4 — Day 18–21：把证据变成获奖作品

# M19 — Streamlit Competition UI

## Page 1 — Solve & Audit

必须显示：

- Hy3 Solution
- Final Answer
- Step-level verdict
- First Root Error
- Error Type
- Evidence
- ROOT / propagated
- Unsupported Answer Warning
- confidence / review hint

## Page 2 — Benchmark Dashboard

- B0 vs Full
- ProcessBench
- TraceAdversarialBench
- difficulty
- error distribution
- efficiency

## Page 3 — Error Explorer

至少支持：

- source
- difficulty
- type
- final/process state
- B0/Full correctness

## 退出标准

- [ ] UI 读取真实 result files
- [ ] 不硬编码指标
- [ ] sample 可追溯
- [ ] API failure 有友好提示
- [ ] 准备至少 2 个稳定 Demo cases

---

# M20 — README / Open-Source Polish

## 首屏结构

### Hook

**Can a correct answer still be wrong?**

### 10 秒理解

- Hy3 solves；
- MathXRay audits；
- external benchmark proves。

### 主结果

第一屏或前两屏出现：

- B0 vs Full 主表；
- 一个 `Final ✓ / Process ✗` case。

### README 必须

- architecture；
- quickstart；
- Hy3 integration；
- data；
- evaluation；
- results；
- reproduction；
- limitations；
- citation/attribution；
- security note。

## 退出标准

- [ ] clean clone 验证
- [ ] `.env.example`
- [ ] 无 key
- [ ] 每个命令真实执行
- [ ] 数据再分发规则清楚

---

# M21 — Final Report

必须覆盖：

1. Motivation
2. Task definition
3. Why final answer accuracy is insufficient
4. Method
5. Hybrid evidence
6. Taxonomy
7. ProcessBench
8. TraceAdversarialBench
9. Ablation
10. Unsupported answers
11. Human audit
12. Difficulty / boundary
13. Efficiency
14. Case studies
15. Failure cases
16. Limitations

## Claim Audit

对每个强 claim 问：

- 哪张表？
- 哪个 sample？
- 哪个 CI？
- 哪个 gold？

无法回答 → 降级措辞或删除。

---

# M22 — ≤120s Demo

## 推荐脚本

### 0–12s — Hook

> “最终答案正确，并不代表推理过程正确。”

### 12–38s — Hy3 Solver

输入题目，展示结构化步骤。

### 38–68s — Root Error

展示：

- Step N ✗
- deterministic evidence
- propagated steps

### 68–88s — Unsupported Answer

展示：

- Final ✓
- Process ✗
- Unsupported

### 88–110s — Benchmark

展示：

- B0 vs Full
- First-Error Exact
- difficulty boundary

### 110–118s — Close

一句话：

> “We evaluate not only whether Hy3 reaches the answer, but whether its reasoning actually supports it.”

## 退出标准

- [ ] 实际 <120s
- [ ] Hy3 角色清晰
- [ ] earliest error 可见
- [ ] `Final ✓ / Process ✗` 可见
- [ ] 至少一个真实 benchmark 数字
- [ ] 不展示未经 frozen result 支持的 claim

---

# M23 — Clean-Room Submission Audit

## 最终模拟评委环境

在新环境：

1. clone；
2. install；
3. 配 env；
4. smoke；
5. run app；
6. load result dashboard；
7. run selected evaluation；
8. check README。

## 检查

- path hardcode；
- API key；
- missing dependency；
- cache assumption；
- OS-specific path；
- missing data；
- broken links；
- outdated numbers；
- demo duration。

## G4 退出标准

- [ ] P0 checklist 全绿
- [ ] external benchmark evidence 完整
- [ ] manual audit 完整
- [ ] README 可复现
- [ ] Demo <120s
- [ ] final report 与 result 一致
- [ ] repo 无敏感信息
- [ ] 不存在“代码写了但从没跑”的核心模块

---

# 9. API / 成本预算策略

为了避免把预算耗在无意义重复实验：

## Ladder

### Smoke

10–30/sample，频繁跑。

### Pilot

50–100/sample，验证方向。

### Dev

200–400/sample，比较模块。

### Formal

冻结后跑 full /正式集。

## 规则

- raw cache 优先；
- metric 改动只重算，不重新调用；
- prompt/model/config 未变不重复生成；
- ablation 先 subset；
- 只有进入最终结果的关键方法才 full run；
- Arbiter selective。

---

# 10. 每日工作闭环

每天结束前记录：

```text
What changed?
Which Requirement?
Which test passed?
Which benchmark changed?
What failed?
What is tomorrow's highest-risk item?
```

每个 CodeBuddy task 结束必须输出：

- changed files；
- tests；
- commands；
- benchmark impact；
- known issues。

完成标准不能是：

> “已实现”。

必须是：

> “在 X 数据/测试上满足 Y 验收，并产生 Z 可追溯结果。”

---

# 11. 风险登记

| 风险 | 严重度 | 早期信号 | 缓解 |
|---|---|---|---|
| ProcessBench label/index 理解错误 | Critical | 手工案例不对齐 | M5 preflight + adapter tests |
| Hy3 API 限流/不稳定 | High | retry/timeout 增加 | cache + resume + batch ladder |
| SymPy coverage 低 | Medium | UNKNOWN 高 | precision-first；只做高价值类型 |
| Semantic Critic false positive 高 | High | Correct Process Acc 低 | conflict arbitration + audit |
| Dependency graph 自己产生错误 | High | root 定位变差 | 只作 evidence；可回退 |
| 自建 mutation 不真实 | High | 人工抽查质量差 | source admission + deterministic validation |
| test contamination | High | formal test 被反复调 prompt | freeze commit/manifest |
| 无过程 gold 却报告 accuracy | Critical | SolveBench “Process Acc”来源不清 | evaluation protocol 强制命名 |
| FPR/FDR 混淆 | Medium | 报告分母不清 | 双指标分开 |
| 过早 UI | High | Week 1 无 baseline | G1 阻断 |
| full benchmark 成本过高 | Medium | dev 已耗大量 API | ladder + cache + selective full |
| 报告 claim 超出结果 | High | “显著/最好”无 CI | Claim Audit |

---

# 12. Stop-Doing Rules

以下任何工作，只要 G1/G2 未通过，都不是主线：

- 高级动画；
- 多 Agent 数量堆叠；
- 本地 Hy3 部署优化；
- 大规模新 benchmark；
- 全量人工标注；
- 完整形式化证明；
- 无失败假设支持的新 verifier；
- 反复重写 README；
- 只为了“架构更复杂”的工程改造。

---

# 13. Award-Level Final Checklist

## Official

- [ ] Hy3 application
- [ ] full solution process
- [ ] standard answers
- [ ] auto verification
- [ ] difficulty stratification
- [ ] process correctness
- [ ] earliest error
- [ ] error taxonomy
- [ ] final-correct/process-invalid
- [ ] localization validation
- [ ] manual false-positive audit
- [ ] final answer accuracy
- [ ] process metric
- [ ] error distribution
- [ ] capability boundary
- [ ] open repo
- [ ] evaluation materials
- [ ] full results
- [ ] audit records
- [ ] analysis report
- [ ] demo <120s

## Evidence

- [ ] B0 Direct Hy3
- [ ] ProcessBench external gold
- [ ] TraceAdversarialBench
- [ ] paired CI
- [ ] ablation
- [ ] failure accounting
- [ ] manual audit
- [ ] raw provenance

## Product

- [ ] Solve & Audit
- [ ] Benchmark Dashboard
- [ ] Error Explorer
- [ ] stable demo cases
- [ ] clean clone

## Story

- [ ] 30s 能说清问题
- [ ] 60s 能说清方法
- [ ] 90s 能展示关键 case
- [ ] 120s 能展示外部证据
- [ ] 任何强 claim 有真实数字支持

---

# 14. 最终执行原则

如果必须在“再做一个功能”和“把已有方法证明得更可信”之间二选一：

> **永远优先后者。**

100 位高校竞争者中真正产生区分度的不是模块数量，而是：

> **官方完成度 + 外部金标准 + earliest-error 证据 + unsupported-answer 能力 + 可控真值 + 人工审计 + 公平消融 + 可复现性 + 极清楚的 Demo。**
