"""Stable first-level error taxonomy (R2.3 / R8)."""

from __future__ import annotations

ERROR_TYPES: tuple[str, ...] = (
    "PROBLEM_MISREAD",
    "CONDITION_OMISSION",
    "CONCEPT_ERROR",
    "THEOREM_MISUSE",
    "LOGIC_GAP",
    "CIRCULAR_REASONING",
    "ALGEBRA_ERROR",
    "ARITHMETIC_ERROR",
    "HALLUCINATION",
    "ANSWER_FORMAT_ERROR",
    "OTHER",
)

ERROR_TYPE_SET = set(ERROR_TYPES)

# Human-readable labels (Chinese) for UI / reports.
ERROR_TYPE_LABELS: dict[str, str] = {
    "PROBLEM_MISREAD": "题意误读",
    "CONDITION_OMISSION": "条件遗漏",
    "CONCEPT_ERROR": "概念错误",
    "THEOREM_MISUSE": "定理误用",
    "LOGIC_GAP": "逻辑跳步",
    "CIRCULAR_REASONING": "循环论证",
    "ALGEBRA_ERROR": "代数变形错误",
    "ARITHMETIC_ERROR": "计算错误",
    "HALLUCINATION": "幻觉/无中生有",
    "ANSWER_FORMAT_ERROR": "答案格式错误",
    "OTHER": "其他",
    "UNKNOWN": "无法可靠分类",
}

PROPAGATION_TAGS = ("ROOT", "PROPAGATED", "INDEPENDENT", "NONE")

# Official-example mapping used in reports (R6 / R8).
OFFICIAL_EXAMPLE_MAP: dict[str, str] = {
    "跳步": "LOGIC_GAP",
    "循环论证": "CIRCULAR_REASONING",
    "误用定理": "THEOREM_MISUSE",
    "条件遗漏": "CONDITION_OMISSION",
    "幻觉": "HALLUCINATION",
    "题意误读": "PROBLEM_MISREAD",
    "概念理解错误": "CONCEPT_ERROR",
    "计算错误": "ARITHMETIC_ERROR",
    "格式不符": "ANSWER_FORMAT_ERROR",
}


def normalize_error_type(value: str | None) -> str | None:
    """Return a canonical taxonomy label, or None when the process is correct."""
    if value is None:
        return None
    raw = str(value).strip().upper().replace(" ", "_").replace("-", "_")
    if raw in {"", "NULL", "NONE", "N/A"}:
        return None
    if raw in ERROR_TYPE_SET:
        return raw
    if raw == "UNKNOWN":
        return "UNKNOWN"
    return "OTHER"
