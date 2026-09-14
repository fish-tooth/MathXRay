# ProcessBench / math

| Metric | Value | 95% CI |
|---|---|---|
| M1 Error Detection Recall | 1.0000 | 1.000 [1.000, 1.000] |
| M2 First-Error Exact | 0.8095 | 0.810 [0.714, 0.905] |
| M3 Correct Process Accuracy | 0.8750 | 0.875 [0.775, 0.975] |
| M4 Process Status Accuracy | 0.9515 | - |
| M5 Official Composite | 0.8350 | - |
| +/-1 Localization | 0.8889 | - |

| Accounting | Value |
|---|---|
| n_all | 103 |
| n_gold_error | 63 |
| n_gold_correct | 40 |
| n_parse_failure | 0 |
| n_api_failure | 0 |
| n_pred_missing | 0 |
| n_missed_localization | 0 |

## Per-source

| Source | Difficulty | M1 | M2 Exact | M3 Correct | M5 | n |
|---|---|---|---|---|---|---|
| math | D3 | 1.0000 | 0.8095 | 0.8750 | 0.8350 | 103 |

## Predicted error-type distribution (no type gold)

| Type | Label | Count |
|---|---|---|
| ALGEBRA_ERROR | 代数变形错误 | 17 |
| CONCEPT_ERROR | 概念错误 | 15 |
| ARITHMETIC_ERROR | 计算错误 | 13 |
| PROBLEM_MISREAD | 题意误读 | 8 |
| THEOREM_MISUSE | 定理误用 | 6 |
| CONDITION_OMISSION | 条件遗漏 | 6 |
| LOGIC_GAP | 逻辑跳步 | 3 |

## Answer / process two-way (gold)

| Cell | n |
|---|---|
| Supported correct (A✓ P✓) | 40 |
| Unsupported answer (A✓ P✗) | 10 |
| Finalization fail (A✗ P✓) | 0 |
| Ordinary fail (A✗ P✗) | 53 |
| Unsupported recall | 1.0000 |