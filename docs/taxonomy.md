# Error Taxonomy v1

> Status: frozen for formal evaluation. Changing a label after freeze requires a new taxonomy version.

## First-level classes

| ID | 中文 | Definition |
|---|---|---|
| `PROBLEM_MISREAD` | 题意误读 | Misreads the goal, objects, or stated conditions. |
| `CONDITION_OMISSION` | 条件遗漏 | Drops a necessary constraint. |
| `CONCEPT_ERROR` | 概念错误 | Wrong mathematical concept. |
| `THEOREM_MISUSE` | 定理误用 | Applies a theorem/formula outside its hypotheses. |
| `LOGIC_GAP` | 逻辑跳步 | Step is not entailed by prior statements. |
| `CIRCULAR_REASONING` | 循环论证 | Uses the claim (or an equivalent) as a premise. |
| `ALGEBRA_ERROR` | 代数变形错误 | Non-equivalent algebraic rewrite. |
| `ARITHMETIC_ERROR` | 计算错误 | Numeric computation error. |
| `HALLUCINATION` | 幻觉 | Introduces a fact not in the problem or prior steps. |
| `ANSWER_FORMAT_ERROR` | 答案格式错误 | Reasoning is fine; the written answer is not. |
| `OTHER` | 其他 | Real error, no better bucket. |
| `UNKNOWN` | 无法分类 | Cannot classify reliably. |

## Independent propagation tags

These are **not** first-level error types:

- `ROOT` — earliest step that introduces a new false inference
- `PROPAGATED` — invalid only because it depends on a root
- `INDEPENDENT` — a later error not caused by the root
- `NONE` — not implicated

## Official-example mapping (R6)

| Official example | Taxonomy |
|---|---|
| 跳步 | `LOGIC_GAP` |
| 循环论证 | `CIRCULAR_REASONING` |
| 误用定理 | `THEOREM_MISUSE` |
| 条件遗漏 | `CONDITION_OMISSION` |
| 幻觉 | `HALLUCINATION` |
| 题意误读 | `PROBLEM_MISREAD` |
| 概念理解错误 | `CONCEPT_ERROR` |
| 计算错误 | `ARITHMETIC_ERROR` |
| 格式不符 | `ANSWER_FORMAT_ERROR` |

Implementation: `src/taxonomy.py`.
