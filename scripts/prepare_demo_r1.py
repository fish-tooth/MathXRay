"""Generate R1 (ReflectiveCritic) demo cases for the app and the demo video.

Runs the real R1 flow against a scripted ``MockProvider`` so every stage
(independent solve → per-paragraph critique → accusation → defence → fusion)
is reproduced offline. No Hy3 quota is consumed, which matters because the
trial quota returns HTTP 402.

Output: ``data/demo_cases_r1.json`` — consumed by ``app.py``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.benchmark.processbench_adapter import CanonicalSample
from src.evaluator.reflective import ReflectiveCritic
from src.llm.mock_provider import MockProvider
from src.verifier.answer_verifier import verify

PROMPT_NAMES = ("independent_solve", "stepwise_critic", "accuser", "defender", "arbiter")


def _j(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False)


# Each case lists the scripted provider responses in R1's call order:
#   independent solve -> stepwise critique -> accuser -> defender -> arbiter
CASES: list[dict] = [
    {
        "id": "r1-supported",
        "title": "过程成立 · 答案正确",
        "headline": "独立求解与学生结论一致，逐段审查全部 VALID，因此不触发对抗轨。",
        "problem": (
            "Chris 的割草机有两种模式。Turtle 模式割完整块草坪要 60 分钟，"
            "Rabbit 模式要 40 分钟。他今天一半用 Turtle、一半用 Rabbit。一共用了多少分钟？"
        ),
        "gold_answer": "50",
        "gold_process_correct": True,
        "gold_first_error_step": None,
        "gold_final_answer_correct": True,
        "steps": [
            "Turtle 模式割完整块草坪需要 60 分钟。",
            "一半草坪在 Turtle 模式下需要 60/2 = 30 分钟。",
            "Rabbit 模式割完整块草坪需要 40 分钟。",
            "一半草坪在 Rabbit 模式下需要 40/2 = 20 分钟。",
            "总时间为 30 + 20 = 50 分钟。",
        ],
        "student_answer": "50",
        "responses": [
            _j(
                {
                    "final_answer": "50",
                    "outline": [
                        "Turtle 半块草坪 60/2 = 30 分钟",
                        "Rabbit 半块草坪 40/2 = 20 分钟",
                        "合计 30 + 20 = 50 分钟",
                    ],
                    "reason": "两种模式各割一半草坪，时间相加。",
                }
            ),
            _j(
                {
                    "steps": [
                        {"step_id": 1, "verdict": "VALID", "claim": "题设给出整块 60 分钟。"},
                        {"step_id": 2, "verdict": "VALID", "claim": "60/2 = 30 正确。"},
                        {"step_id": 3, "verdict": "VALID", "claim": "题设给出整块 40 分钟。"},
                        {"step_id": 4, "verdict": "VALID", "claim": "40/2 = 20 正确。"},
                        {"step_id": 5, "verdict": "VALID", "claim": "30 + 20 = 50 正确。"},
                    ],
                    "reason": "每一步都有题设支撑，无跳步或条件遗漏。",
                }
            ),
        ],
    },
    {
        "id": "r1-root-error",
        "title": "定位最早错误 · 计算失误并传播",
        "headline": "答案是 70，独立求解得 60 —— 结论不一致强制开启指控，符号证据锁定第 2 步。",
        "problem": "一个长方形长 12、宽 5。它的面积是多少？",
        "gold_answer": "60",
        "gold_process_correct": False,
        "gold_first_error_step": 2,
        "gold_final_answer_correct": False,
        "steps": [
            "长方形面积等于长乘宽。",
            "代入长和宽：12*5 = 70。",
            "因此面积为 70。",
        ],
        "student_answer": "70",
        "responses": [
            _j(
                {
                    "final_answer": "60",
                    "outline": ["面积 = 长 × 宽 = 12 × 5", "12 × 5 = 60"],
                    "reason": "直接应用矩形面积公式。",
                }
            ),
            _j(
                {
                    "steps": [
                        {"step_id": 1, "verdict": "VALID", "claim": "矩形面积公式正确。"},
                        {
                            "step_id": 2,
                            "verdict": "INVALID",
                            "claim": "12*5 = 70，实际应为 60。",
                            "error_type": "ARITHMETIC_ERROR",
                        },
                        {"step_id": 3, "verdict": "UNKNOWN", "claim": "沿用了上一步的结果。"},
                    ],
                    "reason": "第 2 步乘法错误。",
                }
            ),
            _j(
                {
                    "charge_stands": True,
                    "first_error_step": 2,
                    "error_type": "ARITHMETIC_ERROR",
                    "charge": "第 2 步声称 12*5 = 70，正确值为 60，差值 10；"
                    "第 3 步只是传播该错误。",
                    "counterexample": "12*5 = 60 ≠ 70",
                }
            ),
            _j({"rebuts": False, "reason": "无法反驳：乘法结果与正确值相差 10。"}),
        ],
    },
    {
        "id": "r1-unsupported",
        "title": "答案正确 · 过程不成立",
        "headline": "最终答案与标准答案一致，但独立求解得到不同结论 —— 指控成立，定位第 3 步。",
        "problem": "已知向量 v = (3, -4)。写出所有与 v 共线的非零向量的一般形式。",
        "gold_answer": "(3λ, -4λ)",
        "gold_process_correct": False,
        "gold_first_error_step": 3,
        "gold_final_answer_correct": True,
        "steps": [
            "与 v 共线的向量可写为 k·v，其中 k 为实数。",
            "代入 v = (3, -4)，得到 (3k, -4k)。",
            "因此答案是 (3λ, -4λ)，λ 为任意实数。",
        ],
        "student_answer": "(3λ, -4λ)",
        "responses": [
            _j(
                {
                    "final_answer": "(3/5, -4/5)",
                    "outline": ["先求 |v| = 5", "单位向量 = v/|v| = (3/5, -4/5)"],
                    "reason": "按单位向量求解。",
                }
            ),
            _j(
                {
                    "steps": [
                        {"step_id": 1, "verdict": "VALID", "claim": "共线向量可表示为数乘。"},
                        {"step_id": 2, "verdict": "VALID", "claim": "代入 v 得 (3k, -4k)。"},
                        {
                            "step_id": 3,
                            "verdict": "INVALID",
                            "claim": "未排除 λ = 0，零向量不是非零向量，答案形式不完整。",
                            "error_type": "ANSWER_FORMAT_ERROR",
                        },
                    ],
                    "reason": "第 3 步遗漏 λ ≠ 0 的约束。",
                }
            ),
            _j(
                {
                    "charge_stands": True,
                    "first_error_step": 3,
                    "error_type": "ANSWER_FORMAT_ERROR",
                    "charge": "第 3 步把 λ 写成任意实数，包含 λ = 0，"
                    "此时得到零向量，题目要求非零向量，答案形式不完整。",
                    "counterexample": "λ = 0 时 (3λ, -4λ) = (0, 0)，不是非零向量。",
                }
            ),
            _j({"rebuts": False, "reason": "确实遗漏了 λ ≠ 0 的约束。"}),
        ],
    },
]


def _load_prompts(prompts_dir: Path) -> dict[str, str]:
    return {name: (prompts_dir / f"{name}.md").read_text(encoding="utf-8") for name in PROMPT_NAMES}


def build_case(case: dict, prompts: dict[str, str]) -> dict:
    sample = CanonicalSample(
        sample_id=case["id"],
        problem=case["problem"],
        steps=case["steps"],
        source="demo",
        gold_process_correct=case["gold_process_correct"],
        gold_first_error_step=case["gold_first_error_step"],
        gold_final_answer_correct=case["gold_final_answer_correct"],
        metadata={"extracted_pred": case["student_answer"]},
    )
    critic = ReflectiveCritic(
        MockProvider(case["responses"]), prompts, model="mock", answer_aware=True
    )
    prediction = critic.judge(sample)
    answer = verify(case["student_answer"], case["gold_answer"])

    return {
        "id": case["id"],
        "title": case["title"],
        "headline": case["headline"],
        "problem": case["problem"],
        "gold_answer": case["gold_answer"],
        "steps": case["steps"],
        "student_answer": case["student_answer"],
        "answer_verdict": answer.verdict.value
        if hasattr(answer.verdict, "value")
        else str(answer.verdict),
        "unsupported_answer": bool(answer.is_equivalent and prediction.process_correct is False),
        "audit": prediction.to_dict(),
        "gold": {
            "process_correct": case["gold_process_correct"],
            "first_error_step": case["gold_first_error_step"],
            "final_answer_correct": case["gold_final_answer_correct"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompts-dir", default="prompts")
    parser.add_argument("--out", default="data/demo_cases_r1.json")
    args = parser.parse_args(argv)

    prompts = _load_prompts(Path(args.prompts_dir))
    payload = {"method": "R1-ReflectiveCritic", "cases": [build_case(c, prompts) for c in CASES]}

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    for case in payload["cases"]:
        audit = case["audit"]
        print(
            f"{case['id']}: process_correct={audit['process_correct']} "
            f"first_error={audit['first_error_step']} type={audit['error_type']} "
            f"debate={audit['extra'].get('debate_triggered')} "
            f"unsupported={case['unsupported_answer']}"
        )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
