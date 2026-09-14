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
