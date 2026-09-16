# SolveBench / TraceAdversarialBench / Demo data

This directory holds **evaluation materials** required by the contest:

- stratified problem sets with gold answers
- mutation traces with programmatic gold first-error / type
- demo cases for the <120s video

## Layout

```
data/
  README.md                 # this file
  demo_cases.json           # three frozen UI demo traces
  processed/
    solvebench.jsonl        # generated: GSM8K + MATH + Omni-MATH subset
    solvebench.manifest.json
    adversarial.jsonl       # generated: TraceAdversarialBench
    adversarial.manifest.json
```

`data/raw/` is gitignored (HF cache / non-redistributable dumps).

## SolveBench construction

Command:

```bash
python scripts/prepare_solvebench.py --n 90 --seed 42
```

| Source | Split preference | Difficulty (frozen) | Gold | Verifier |
|---|---|---|---|---|
| GSM8K (`openai/gsm8k`) | test | **D1** | `####` tail | numeric |
| MATH (`hendrycks/competition_math`) | test | level 1–2 → **D2**, 3 → **D3**, 4–5 → **D4** | last `\boxed{}` | auto (exact/numeric/sympy) |
| Omni-MATH | test/train | **D5** | `answer` or boxed | auto |

Sampling: stratified by difficulty, seed 42. If API budget is limited this frozen subset is the registered formal set; it is **not** re-sampled after seeing results.

Licenses are recorded per row (`license_or_citation`). Do not republish datasets that forbid redistribution; the prep script downloads from Hugging Face at eval time.

## Private high-school corpus (local only)

`data/high_school_all_annotated_final.json` is gitignored. It contains 4300 高中数学题、官方详解，以及字段 `step_by_step_solution_gpt4o.Solution_Steps` 中的模型逐步解答（无专家首错标注）。

```bash
python scripts/prepare_highschool.py --stage pilot
python scripts/run_highschool_b0.py --stage pilot
python scripts/run_highschool_reflective.py --stage smoke
```

`R1-ReflectiveCritic` 在高中切片上开启 answer-aware：答案核失败会强制指控/辩护，不允许再把过程判成成立。独立求解只作私有脚手架，不把官方答案写进 prompt。

评测切片写入 `data/processed/highschool_pilot.jsonl`（亦 gitignore）。金标准口径见该文件对应 manifest：答案错 → 过程错（无首错位置）；官方详解 → 弱正确过程；确定性 mutation → 可编程首错。

## TraceAdversarialBench

Command:

```bash
python scripts/build_adversarial.py --n 80 --seed 42
```

Source traces: ProcessBench rows with `label == -1` (gold-correct process). Mutations:

| Mutation | Gold type | Answer-preserving? |
|---|---|---|
| arithmetic number perturb | `ARITHMETIC_ERROR` | no |
| sign flip | `ARITHMETIC_ERROR` | no |
| operator swap | `ALGEBRA_ERROR` | no |
| unused `2+2=5` claim | `HALLUCINATION` | **yes** |

Gold `first_error_step` is the mutated 1-based index. Dev/test split is the ProcessBench source split of the parent trace.

## Demo cases

`demo_cases.json` contains three replay traces used by `app.py` so the video does not depend on live API latency:

1. Supported correct (Final ✓ / Process ✓)
2. Arithmetic root error with propagated follow-up
3. Unsupported answer (Final ✓ / Process ✗)
