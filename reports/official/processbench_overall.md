# ProcessBench B0 Direct-Judge (three-dataset overall)

| Metric | Value | 95% CI |
|---|---|---|
| M1 Error Detection Recall | 0.9569 | 0.957 [0.927, 0.983] |
| M2 First-Error Exact | 0.7543 | 0.754 [0.698, 0.806] |
| M3 Correct Process Accuracy | 0.8803 | 0.880 [0.821, 0.940] |
| M4 Process Status Accuracy | 0.9312 | - |
| M5 Official Composite | 0.7966 | - |
| +/-1 Localization | 0.8448 | - |

| Accounting | Value |
|---|---|
| n_all | 349 |
| n_gold_error | 232 |
| n_gold_correct | 117 |
| n_parse_failure | 8 |
| n_api_failure | 0 |
| n_pred_missing | 0 |
| n_missed_localization | 10 |

## Per-source

| Source | Difficulty | M1 | M2 Exact | M3 Correct | M5 | n |
|---|---|---|---|---|---|---|
| gsm8k | D1 | 1.0000 | 0.8421 | 1.0000 | 0.9167 | 36 |
| math | D3 | 1.0000 | 0.8095 | 0.8750 | 0.8350 | 103 |
| olympiadbench | D4 | 0.9104 | 0.6866 | 0.8947 | 0.7619 | 105 |
| omnimath | D5 | 0.9518 | 0.7470 | 0.7727 | 0.7524 | 105 |

## Predicted error-type distribution (no type gold)

| Type | Label | Count |
|---|---|---|
| CONCEPT_ERROR | 概念错误 | 70 |
| PROBLEM_MISREAD | 题意误读 | 36 |
| ALGEBRA_ERROR | 代数变形错误 | 33 |
| ARITHMETIC_ERROR | 计算错误 | 31 |
| CONDITION_OMISSION | 条件遗漏 | 28 |
| LOGIC_GAP | 逻辑跳步 | 19 |
| THEOREM_MISUSE | 定理误用 | 12 |
| HALLUCINATION | 幻觉/无中生有 | 6 |
| CIRCULAR_REASONING | 循环论证 | 1 |

## Answer / process two-way (gold)

| Cell | n |
|---|---|
| Supported correct (A✓ P✓) | 117 |
| Unsupported answer (A✓ P✗) | 55 |
| Finalization fail (A✗ P✓) | 0 |
| Ordinary fail (A✗ P✗) | 177 |
| Unsupported recall | 0.9091 |

## Capability boundary

Largest adjacent First-Error Exact drop: D3 (math, 0.8095) → D4 (olympiadbench, 0.6866), drop = 0.1230.