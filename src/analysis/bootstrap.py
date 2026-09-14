"""Bootstrap confidence intervals for rates (EXT-07)."""

from __future__ import annotations

import random
from collections.abc import Sequence


def bootstrap_ci(
    successes: Sequence[int],
    *,
    n_boot: int = 2000,
    seed: int = 42,
    alpha: float = 0.05,
) -> tuple[float | None, float | None, float | None]:
    """Return (point, low, high) for a Bernoulli mean. None if empty."""
    n = len(successes)
    if n == 0:
        return None, None, None
    point = sum(successes) / n
    rng = random.Random(seed)
    stats: list[float] = []
    for _ in range(n_boot):
        total = 0
        for _i in range(n):
            total += successes[rng.randrange(n)]
        stats.append(total / n)
    stats.sort()
    lo_idx = int(alpha / 2 * n_boot)
    hi_idx = int((1 - alpha / 2) * n_boot) - 1
    lo_idx = min(max(lo_idx, 0), n_boot - 1)
    hi_idx = min(max(hi_idx, 0), n_boot - 1)
    return point, stats[lo_idx], stats[hi_idx]


def fmt_ci(point: float | None, lo: float | None, hi: float | None) -> str:
    if point is None:
        return "-"
    if lo is None or hi is None:
        return f"{point:.3f}"
    return f"{point:.3f} [{lo:.3f}, {hi:.3f}]"
