# MathXRay

<img src="docs/figures/logo.svg" width="36" height="36" alt="MathXRay logo" align="left" />

**MathXRay** 用 Hy3 做数学解题，并对写出的步骤做过程审查：核对最终答案，判断推理是否成立，标出最早出错的那一步，标出答案对了但过程撑不住的样本。

Hy3 在项目中有两个角色：

1. **Solver**：输出结构化的 `solution_steps` 和 `final_answer`
2. **Critic**：审查这些步骤

审查有两套，可以切换：

| | B0 Direct Judge | R1 Reflective Critic |
|---|---|---|
| 做法 | 一次看完全文，直接给出过程对错、首错步、错误类型 | 独立求解 → 逐段 VALID/INVALID/UNKNOWN → 必要时指控 / 辩护 / 仲裁 → 按规则汇总 |
| 公开评测 | ProcessBench 主结果 | 尚未在 ProcessBench 上运行 |
| 应用 | 可选 | 默认引擎 |

参考答案不写入审查提示。私有高中评测里，若学生答案已经和参考答案对不上，R1 不允许再把过程判成成立。能用计算证伪的步骤优先于模型口头判断。

![演示](demo/mathxray.gif)

## 怎么跑

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
copy .env.example .env
```

在 `.env` 中填写 `HY3_API_KEY`、`HY3_BASE_URL`、`HY3_MODEL`。不要把 `.env` 提交进仓库。

```bash
streamlit run app.py
```

浏览器打开本地地址后有四个页面：

| 页面 | 作用 |
|---|---|
| 解题与审计 | 选 R1 或 B0。演示案例不调接口；现场解题需要 Hy3 |
| 评测看板 | 读取 `reports/official/`，以及私有集对照 `reports/highschool_compare.json` |
| 错误探索 | 按来源、过程状态、错误类型筛选 `results/raw` |
| 演示分镜 | 框架说明、应用例题、评测图（`?page=story&slide=0`） |

演示案例：R1 用 `data/demo_cases_r1.json`（割草机 / 矩形面积 / 共线向量），B0 用 `data/demo_cases.json`。

离线检查：

```bash
pytest
python scripts/run_b0_baseline.py --stage smoke --provider mock
```

重新截取 GIF：先启动应用，再 `python scripts/capture_demo_gif.py --base http://127.0.0.1:8501`（需要本机 Chrome 和 selenium）。

## 审查流程

```mermaid
flowchart TD
    U[题目] --> S[Hy3 Solver]
    S --> T[步骤 + 最终答案]
    T --> FA[答案校验]
    T --> B0[B0 一次判断]
    T --> R1[R1 四段审查]

    subgraph r1flow [R1]
        I[独立求解<br/>看不到学生步骤]
        W[逐段审查]
        D[指控 / 辩护 / 仲裁]
        F[规则汇总]
        I --> W --> D --> F
    end

    R1 --> r1flow
    B0 --> H[符号检查 + 一次判断 + 依赖图]
    F --> OUT[过程是否成立 / 最早错步 / 类型 / 跟着错]
    H --> OUT
    FA --> UA[答案对错 · unsupported]
```

R1 对质只在这些情况下打开：独立结论和学生答案对不上、某段是 UNKNOWN、或答案校验失败。汇总顺序：符号 INVALID → 仲裁 → 未反驳的指控 → 逐段第一个 INVALID → 答案对不上则过程不能成立。

## 数据集

评测分公开集和一份只在本地使用的私有高中语料。构造说明见 [`data/README.md`](data/README.md)，指标口径见 [`docs/evaluation_protocol.md`](docs/evaluation_protocol.md)。

### ProcessBench

第三方过程评测。每条样本带「最早错误步号」（从 0 计，过程成立为 −1）。本仓库使用分层切片，而不是全量约 3400 条。

| 来源 | 难度 | 切片条数 | 内容 |
|---|---|---:|---|
| GSM8K | D1 | 36 | 小学应用题 |
| MATH | D3 | 103 | 竞赛数学 |
| Omni-MATH | D5 | 105 | 更难的奥林匹克风格 |
| 三集合计 | — | **244** | 对外主表 |
| OlympiadBench | D4 | 105 | 附加高难 split，写入总表 n=349 |

切片构成：

```mermaid
pie title ProcessBench 三数据集切片 n=244
  "GSM8K 36" : 36
  "MATH 103" : 103
  "Omni-MATH 105" : 105
```

Gold 侧（三数据集）：过程有错 165，过程成立 79；其中答案对但过程不成立 37 条。

入口：`scripts/run_b0_baseline.py`，`scripts/aggregate_official.py`。正式数字在 [`reports/official/`](reports/official/)，由 `results/raw` 重算。

### SolveBench

用来看 Hy3 **解题**能力，和过程审查分开记账。从 GSM8K / MATH / Omni-MATH 按难度分层抽样，seed 42，默认 90 道，带标准答案。

```bash
python scripts/prepare_solvebench.py --n 90 --seed 42
python scripts/run_solvebench.py --max-samples 90
```

输出：`data/processed/solvebench.jsonl`。

### TraceAdversarialBench

在 ProcessBench 过程成立的轨迹上注入可控错误，得到可编程的首错步和错误类型。

| 改法 | 类型 | 是否保持答案 |
|---|---|---|
| 改数字 | 计算错误 | 否 |
| 改符号 | 计算错误 | 否 |
| 换运算符 | 代数错误 | 否 |
| 插入无关式子 | 幻觉 | 是 |

默认 80 条，seed 42。入口：`scripts/build_adversarial.py`，`scripts/run_adversarial.py`。

### 私有高中题集（本地）

来源文件 `data/high_school_all_annotated_final.json` 已 gitignore，不公开、不进远程。约 4300 道高中选择 / 填空，带官方详解，以及模型逐步解答。没有人工标注「哪一步开始错」。

有逐步解答的约 **4297** 道，按模型答案和参考答案能否对齐：

![私有语料构成](docs/figures/highschool_corpus.svg)

| 字段 / 子集 | 规模 | 说明 |
|---|---:|---|
| 有逐步解答 | 4297 | 评测只使用这些 |
| 模型答案与参考一致 | 1343 | 过程好不好仍未知 |
| 模型答案与参考不一致 | 370 | 过程至少有问题 |
| 答案能否对齐不确定 | 2584 | 形式或抽取对不上 |
| 冻结评测切片 | 88 | seed 42，见下表 |

冻结切片 `data/processed/highschool_{smoke,pilot}.jsonl` 同样 gitignore：

| 子集 | smoke | pilot | 能看什么 |
|---|---:|---:|---|
| 模型答案已经算错 | 6 | 28 | 能不能发现过程有问题 |
| 模型答案算对了 | 6 | 28 | 会不会把对的过程判错 |
| 官方详解 | 6 | 16 | 会不会把教材步骤判不成立 |
| 在官方步骤上改错 | 6 | 16 | 能不能指到被改的那一步 |

```bash
python scripts/prepare_highschool.py --stage pilot
python scripts/run_highschool_b0.py --stage pilot --provider hy3
python scripts/run_highschool_reflective.py --stage pilot --provider hy3
```

R1 在该切片上开启 `answer_aware`：答案对不上则过程不能成立。对照表：[`reports/highschool_compare.json`](reports/highschool_compare.json)，说明：[`reports/experiment_report.md`](reports/experiment_report.md)。

## 实验结果

### ProcessBench（B0，Hy3）

三数据集 n=244：

| 指标 | 数值 | 95% CI |
|---|---|---|
| 发现过程有错 M1 | 0.976 | [0.952, 0.994] |
| 指出最早错步 M2 | 0.782 | [0.715, 0.842] |
| 放过正确过程 M3 | 0.873 | [0.797, 0.937] |
| 过程状态准确率 M4 | 0.943 | — |
| 综合 M5 | 0.811 | — |

![指出首错随数据集](docs/figures/processbench_m2.svg)

| 来源 | M1 | M2 | M3 | n |
|---|---|---|---|---:|
| GSM8K | 1.00 | 0.84 | 1.00 | 36 |
| MATH | 1.00 | 0.81 | 0.88 | 103 |
| Omni-MATH | 0.95 | 0.75 | 0.77 | 105 |
| OlympiadBench | 0.91 | 0.69 | 0.89 | 105 |

加上 OlympiadBench 后 n=349，M2 约 0.75。答案对但过程不成立的样本，三数据集上召回约 0.92。预测错误类型里，概念错误、题意误读、计算错误较多，完整表见 [`reports/official/processbench_three_datasets.md`](reports/official/processbench_three_datasets.md)。

### 私有高中切片（B0 与 R1，同一 88 道、同一 Hy3）

![B0 与 R1 对照](docs/figures/highschool_compare.svg)

| | B0 | R1 |
|---|---|---|
| 答案错误：发现过程有问题 | 4/28（0.14） | 28/28（1.00） |
| 改错样本：指到被改的那一步 | 11/16（0.69） | 12/16（0.75） |
| 官方详解：认为过程成立 | 7/16（0.44） | 6/16（0.38） |
| 后两行调和平均 | 0.54 | 0.50 |
| 答案正确样本被判过程错 | 4/28 | 5/28 |

R1 在「答案已经算错」的 28 道上全部判有问题，其中约 18 道是答案规则改判的，逐步审查自己标 INVALID 的大约 5 道。改错 16 道上，定位主要靠逐段审查。官方详解上 R1 更严，所以两项折中略低于 B0。这批数字用来看失败模式和调提示，不能代替 ProcessBench 主表。R1 也还没有在 ProcessBench 上评过。

## 仓库导读

```
app.py                      四个页面
configs/default.yaml        温度、超时、路径
prompts/                    solver、direct_judge、independent_solve、
                            stepwise_critic、accuser、defender、arbiter
src/factory.py              组装 Solver / B0 / R1
src/pipeline.py             MathXRayPipeline（B0）、ReflectivePipeline（R1）
src/evaluator/              一次判断、混合融合、四段审查、符号、依赖图
src/llm/                    Hy3 客户端与 mock
scripts/                    评测、切片、GIF
data/demo_cases*.json       应用演示
reports/official/           对外数字
demo/mathxray.gif
docs/figures/               README 用图
```

| 脚本 | 作用 |
|---|---|
| `run_b0_baseline.py` | ProcessBench B0 |
| `aggregate_official.py` | 从 raw 重算 official |
| `prepare_highschool.py` | 冻结高中切片 |
| `run_highschool_b0.py` / `run_highschool_reflective.py` | 高中集 B0 / R1 |
| `prepare_demo_r1.py` | 生成 R1 演示 JSON |
| `capture_demo_gif.py` | 截取 GIF |
| `prepare_solvebench.py` / `run_solvebench.py` | 解题评测 |
| `build_adversarial.py` / `run_adversarial.py` | 可控改错集 |

`results/raw/` 体积大，已 gitignore，本地不要删。评测可按样本 + 方法 + 运行签名续跑。

## 总结

MathXRay 把「算出答案」和「步骤是否成立」分开处理。B0 一次判断已经能在 ProcessBench 上较高比例地发现错误，中等比例地指出第一处错误；难度上去，定位会下降。R1 把审查拆开，应用里可以顺着独立求解、逐段标记和对质往回看。私有高中集上，R1 更会抓住答案已经错了和形式没收齐的解答，对官方详解更严，综合没有超过 B0。参考答案不进提示，答案对不上只作为过程不能成立的开关。

## 下一步

1. 在 ProcessBench 上跑 R1，和 B0 用同一套公开口径对照。
2. 放松逐步审查和指控对教材跳步的处理，减少把官方详解判错。
3. 把「答案对不上」和「指出第几步」继续分列，避免把规则改判算进定位。
4. 为形式不完整单独设一类错误，并在提示里写清收束要求。
5. 若要在私有集上认真报定位，需要逐步对错的人工标注，或扩大可控改错子集。

## 引用

- ProcessBench: Qwen/ProcessBench
- GSM8K, MATH, Omni-MATH, OlympiadBench：见各数据集说明
- Hy3: https://github.com/Tencent-Hunyuan/Hy3
