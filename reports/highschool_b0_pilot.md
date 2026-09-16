# High-school B0 Direct-Judge (pilot)

Frozen slice: `data/processed/highschool_pilot.jsonl` (seed 42, n=88).
Raw: `results/raw/B0-HighSchool_pilot.jsonl`.
Live Hy3 run: `B0-HighSchool-20260915T004828Z-b2e66a2b` (resume 26 + new 62).

Do **not** cite the mixed 88-row metrics: `qwen_right` has no process gold, and `qwen_wrong` has no first-error gold.

## Gold protocol (ProcessBench-adapted)

| Track | n | Gold | Honest metrics |
|---|---:|---|---|
| qwen_wrong | 28 | extracted answer ≠ official answer ⇒ process invalid; first-error unknown | **M1 only** |
| qwen_right | 28 | unlabeled process | unsupported *candidates* only |
| official | 16 | textbook analysis as weak gold-correct | M3 |
| adversarial | 16 | deterministic mutation of official traces | M1 / **M2** |

ProcessBench headline ≈ harmonic mean of error-set exact-index accuracy and correct-set accuracy. Here that probe is **adversarial M2** with **official M3**.

## Hy3 B0 result (complete)

| Track | n | parse_fail | Metric | Value |
|---|---:|---:|---|---:|
| qwen_wrong | 28 | 1 | M1 error-detection recall (ITT) | **0.143** (4/28) |
| official | 16 | 2 | M3 correct-process accuracy | **0.438** (7/16) |
| adversarial | 16 | 1 | M1 / M2 | **0.812** / **0.688** |
| qwen_right | 28 | 3 | flagged process-invalid (unsupported) | 4/28 = 0.143; accepted 21 |

ProcessBench-style probe F1 (adversarial M2 ∧ official M3): **0.535**.

Reading:

- **qwen_wrong M1 stays 0.143.** Single-shot JSON still accepts most answer-wrong traces. Completeness / answer-form misses (e.g. `(3λ,-4λ)` vs one vector) are the typical failure.
- **official M3 0.438.** B0 over-flags textbook analyses as invalid; this will drag any ProcessBench-style F1 even if localization on mutations looks decent.
- **adversarial M2 0.688** is the only first-error number that is actually gold-backed on this corpus.

## R1 smoke (live Hy3, n=24)

Run `R1-ReflectiveCritic-20260915T012739Z-408ea2dc`, 44 min, 24 new / 0 resumed.

| Track | n | R1 | B0 (pilot n=88, not the same slice) |
|---|---:|---|---|
| qwen_wrong M1 | 6 | **1.000** | 0.143 |
| official M3 | 6 | **0.000** | 0.438 |
| adversarial M1 / M2 | 6 | **1.000 / 1.000** | 0.812 / 0.688 |
| probe F1 | | **0.000** (M3=0) | 0.535 |

Honest reading: qwen_wrong M1 is almost entirely the **answer-mismatch gate**. 5/6 of those traces were stepwise-VALID; fusion then forced INVALID (`ANSWER_FORMAT_ERROR`). That is not ProcessBench localization. Official textbook traces were all flagged INVALID (stepwise over-picky). Adversarial first-error on n=6 matched the mutated step every time — the only gold-backed localization win, still too small to cite as a result.

```bash
python scripts/run_highschool_reflective.py --stage pilot --provider hy3
```
