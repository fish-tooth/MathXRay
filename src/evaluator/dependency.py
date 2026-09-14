"""Dependency graph and root / propagated / independent tagging (M9 / EXT-04)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StepDependency:
    step_id: int
    depends_on: list[int] = field(default_factory=list)
    tag: str = "NONE"  # ROOT | PROPAGATED | INDEPENDENT | NONE


@dataclass
class DependencyGraph:
    steps: list[StepDependency]
    first_root_error: int | None = None
    ok: bool = True
    error: str | None = None

    def tag_for(self, step_id: int) -> str:
        for step in self.steps:
            if step.step_id == step_id:
                return step.tag
        return "NONE"


def _default_depends(n: int, explicit: dict[int, list[int]] | None) -> dict[int, list[int]]:
    """Sequential fallback: step k depends on k-1 when the solver omitted edges."""
    edges = {i: list(explicit.get(i, [])) for i in range(1, n + 1)} if explicit else {
        i: ([i - 1] if i > 1 else []) for i in range(1, n + 1)
    }
    if explicit:
        for i in range(1, n + 1):
            if i not in explicit and i > 1 and not edges[i]:
                edges[i] = [i - 1]
    # Drop self-edges and out-of-range ids.
    cleaned: dict[int, list[int]] = {}
    for sid, deps in edges.items():
        cleaned[sid] = [d for d in deps if 1 <= d < sid]
    return cleaned


def descendants(edges: dict[int, list[int]], root: int) -> set[int]:
    """Return steps that (transitively) depend on ``root``."""
    children: dict[int, list[int]] = {k: [] for k in edges}
    for sid, deps in edges.items():
        for d in deps:
            children.setdefault(d, []).append(sid)
    seen: set[int] = set()
    stack = list(children.get(root, []))
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        stack.extend(children.get(cur, []))
    return seen


def build_graph(
    n_steps: int,
    *,
    first_error_step: int | None,
    extra_error_steps: list[int] | None = None,
    depends_on: dict[int, list[int]] | None = None,
) -> DependencyGraph:
    """Tag steps relative to the earliest error.

    - ROOT: the earliest error step
    - PROPAGATED: downstream steps that depend on the root
    - INDEPENDENT: later errors that do not depend on the root
    - NONE: steps that are not implicated (including a fully correct trace)
    """
    if n_steps < 1:
        return DependencyGraph(steps=[], ok=False, error="empty trace")

    edges = _default_depends(n_steps, depends_on)
    nodes = [
        StepDependency(step_id=i, depends_on=edges.get(i, []))
        for i in range(1, n_steps + 1)
    ]

    if first_error_step is None:
        return DependencyGraph(steps=nodes, first_root_error=None)

    if not (1 <= first_error_step <= n_steps):
        return DependencyGraph(
            steps=nodes,
            first_root_error=None,
            ok=False,
            error=f"first_error_step {first_error_step} out of range",
        )

    downstream = descendants(edges, first_error_step)
    extra = {s for s in (extra_error_steps or []) if s != first_error_step}

    for node in nodes:
        if node.step_id == first_error_step:
            node.tag = "ROOT"
        elif node.step_id in extra and node.step_id not in downstream:
            node.tag = "INDEPENDENT"
        elif node.step_id in downstream:
            node.tag = "PROPAGATED"
        else:
            node.tag = "NONE"

    return DependencyGraph(steps=nodes, first_root_error=first_error_step)
