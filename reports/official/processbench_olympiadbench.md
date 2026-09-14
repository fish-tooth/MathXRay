# ProcessBench / olympiadbench

| Metric | Value | 95% CI |
|---|---|---|
| M1 Error Detection Recall | 0.9104 | 0.910 [0.836, 0.970] |
| M2 First-Error Exact | 0.6866 | 0.687 [0.567, 0.791] |
| M3 Correct Process Accuracy | 0.8947 | 0.895 [0.789, 0.974] |
| M4 Process Status Accuracy | 0.9048 | - |
| M5 Official Composite | 0.7619 | - |
| +/-1 Localization | 0.7910 | - |

| Accounting | Value |
|---|---|
| n_all | 105 |
| n_gold_error | 67 |
| n_gold_correct | 38 |
| n_parse_failure | 6 |
| n_api_failure | 0 |
| n_pred_missing | 0 |
| n_missed_localization | 6 |

## Per-source

| Source | Difficulty | M1 | M2 Exact | M3 Correct | M5 | n |
|---|---|---|---|---|---|---|
| olympiadbench | D4 | 0.9104 | 0.6866 | 0.8947 | 0.7619 | 105 |

## Predicted error-type distribution (no type gold)

| Type | Label | Count |
|---|---|---|
| CONCEPT_ERROR | 概念错误 | 17 |
| ALGEBRA_ERROR | 代数变形错误 | 11 |
| CONDITION_OMISSION | 条件遗漏 | 10 |
| PROBLEM_MISREAD | 题意误读 | 8 |
| ARITHMETIC_ERROR | 计算错误 | 7 |
| LOGIC_GAP | 逻辑跳步 | 6 |
| THEOREM_MISUSE | 定理误用 | 4 |
| HALLUCINATION | 幻觉/无中生有 | 2 |

## Answer / process two-way (gold)

| Cell | n |
|---|---|
| Supported correct (A✓ P✓) | 38 |
| Unsupported answer (A✓ P✗) | 18 |
| Finalization fail (A✗ P✓) | 0 |
| Ordinary fail (A✗ P✗) | 49 |
| Unsupported recall | 0.8889 |