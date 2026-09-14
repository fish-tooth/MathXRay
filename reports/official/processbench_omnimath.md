# ProcessBench / omnimath

| Metric | Value | 95% CI |
|---|---|---|
| M1 Error Detection Recall | 0.9518 | 0.952 [0.904, 0.988] |
| M2 First-Error Exact | 0.7470 | 0.747 [0.651, 0.831] |
| M3 Correct Process Accuracy | 0.7727 | 0.773 [0.591, 0.955] |
| M4 Process Status Accuracy | 0.9143 | - |
| M5 Official Composite | 0.7524 | - |
| +/-1 Localization | 0.8434 | - |

| Accounting | Value |
|---|---|
| n_all | 105 |
| n_gold_error | 83 |
| n_gold_correct | 22 |
| n_parse_failure | 2 |
| n_api_failure | 0 |
| n_pred_missing | 0 |
| n_missed_localization | 4 |

## Per-source

| Source | Difficulty | M1 | M2 Exact | M3 Correct | M5 | n |
|---|---|---|---|---|---|---|
| omnimath | D5 | 0.9518 | 0.7470 | 0.7727 | 0.7524 | 105 |

## Predicted error-type distribution (no type gold)

| Type | Label | Count |
|---|---|---|
| CONCEPT_ERROR | 概念错误 | 37 |
| PROBLEM_MISREAD | 题意误读 | 12 |
| ARITHMETIC_ERROR | 计算错误 | 9 |
| LOGIC_GAP | 逻辑跳步 | 8 |
| CONDITION_OMISSION | 条件遗漏 | 6 |
| ALGEBRA_ERROR | 代数变形错误 | 5 |
| HALLUCINATION | 幻觉/无中生有 | 4 |
| THEOREM_MISUSE | 定理误用 | 2 |
| CIRCULAR_REASONING | 循环论证 | 1 |

## Answer / process two-way (gold)

| Cell | n |
|---|---|
| Supported correct (A✓ P✓) | 22 |
| Unsupported answer (A✓ P✗) | 27 |
| Finalization fail (A✗ P✓) | 0 |
| Ordinary fail (A✗ P✗) | 56 |
| Unsupported recall | 0.8889 |