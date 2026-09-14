# ProcessBench / gsm8k

| Metric | Value | 95% CI |
|---|---|---|
| M1 Error Detection Recall | 1.0000 | 1.000 [1.000, 1.000] |
| M2 First-Error Exact | 0.8421 | 0.842 [0.684, 1.000] |
| M3 Correct Process Accuracy | 1.0000 | 1.000 [1.000, 1.000] |
| M4 Process Status Accuracy | 1.0000 | - |
| M5 Official Composite | 0.9167 | - |
| +/-1 Localization | 0.8947 | - |

| Accounting | Value |
|---|---|
| n_all | 36 |
| n_gold_error | 19 |
| n_gold_correct | 17 |
| n_parse_failure | 0 |
| n_api_failure | 0 |
| n_pred_missing | 0 |
| n_missed_localization | 0 |

## Per-source

| Source | Difficulty | M1 | M2 Exact | M3 Correct | M5 | n |
|---|---|---|---|---|---|---|
| gsm8k | D1 | 1.0000 | 0.8421 | 1.0000 | 0.9167 | 36 |

## Predicted error-type distribution (no type gold)

| Type | Label | Count |
|---|---|---|
| PROBLEM_MISREAD | 题意误读 | 8 |
| CONDITION_OMISSION | 条件遗漏 | 6 |
| LOGIC_GAP | 逻辑跳步 | 2 |
| ARITHMETIC_ERROR | 计算错误 | 2 |
| CONCEPT_ERROR | 概念错误 | 1 |

## Answer / process two-way (gold)

| Cell | n |
|---|---|
| Supported correct (A✓ P✓) | 17 |
| Unsupported answer (A✓ P✗) | 0 |
| Finalization fail (A✗ P✓) | 0 |
| Ordinary fail (A✗ P✗) | 19 |
| Unsupported recall | - |