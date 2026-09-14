# Three datasets: GSM8K + MATH + Omni-MATH

| Metric | Value | 95% CI |
|---|---|---|
| M1 Error Detection Recall | 0.9758 | 0.976 [0.952, 0.994] |
| M2 First-Error Exact | 0.7818 | 0.782 [0.715, 0.842] |
| M3 Correct Process Accuracy | 0.8734 | 0.873 [0.797, 0.937] |
| M4 Process Status Accuracy | 0.9426 | - |
| M5 Official Composite | 0.8115 | - |
| +/-1 Localization | 0.8667 | - |

| Accounting | Value |
|---|---|
| n_all | 244 |
| n_gold_error | 165 |
| n_gold_correct | 79 |
| n_parse_failure | 2 |
| n_api_failure | 0 |
| n_pred_missing | 0 |
| n_missed_localization | 4 |

## Per-source

| Source | Difficulty | M1 | M2 Exact | M3 Correct | M5 | n |
|---|---|---|---|---|---|---|
| gsm8k | D1 | 1.0000 | 0.8421 | 1.0000 | 0.9167 | 36 |
| math | D3 | 1.0000 | 0.8095 | 0.8750 | 0.8350 | 103 |
| omnimath | D5 | 0.9518 | 0.7470 | 0.7727 | 0.7524 | 105 |

## Predicted error-type distribution (no type gold)

| Type | Label | Count |
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

## Answer / process two-way (gold)

| Cell | n |
|---|---|
| Supported correct (A✓ P✓) | 79 |
| Unsupported answer (A✓ P✗) | 37 |
| Finalization fail (A✗ P✓) | 0 |
| Ordinary fail (A✗ P✗) | 128 |
| Unsupported recall | 0.9189 |

## Capability boundary

Largest adjacent First-Error Exact drop: D3 (math, 0.8095) → D5 (omnimath, 0.7470), drop = 0.0625.