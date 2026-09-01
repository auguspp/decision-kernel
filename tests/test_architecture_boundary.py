from __future__ import annotations

import ast
from pathlib import Path


def _relative_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.level > 0
    }


def test_decision_spine_does_not_depend_on_research_method_v1() -> None:
    workflow = Path("src/decision_kernel/workflow.py")
    imports = _relative_imports(workflow)

    assert "deep_research" not in imports
    assert "research_funnel" not in imports
    assert "research_contract_v1" not in imports
    assert "research_workflow_v1" not in imports


def test_research_method_v1_depends_on_decision_spine_not_reverse() -> None:
    method_workflow = Path("src/decision_kernel/research_workflow_v1.py")
    imports = _relative_imports(method_workflow)

    assert "workflow" in imports


def test_research_commit_stays_method_agnostic_and_runtime_free() -> None:
    research_commit = Path("src/decision_kernel/research_commit.py")
    imports = _relative_imports(research_commit)

    # `rehearsal` is currently allowed only because framing is a one-file CLI
    # convenience. Research identity and commit authority must not depend on
    # executable composition, providers, market data, or default policy.
    allowed = {
        "evidence",
        "identity",
        "primitives",
        "rehearsal",
        "research",
    }
    assert imports <= allowed


def test_live_remains_an_explicit_composition_root() -> None:
    live = Path("src/decision_kernel/live.py")
    imports = _relative_imports(live)

    # Adding a new local dependency here should be an explicit architecture
    # decision. `live.py` may wire existing capabilities; it must not quietly
    # grow scheduler, persistence, retry/fallback, Radar, or notification logic.
    allowed = {
        "adapters.hithink",
        "authority",
        "deep_research",
        "market",
        "policy",
        "primitives",
        "rehearsal",
        "research_commit",
        "research_workflow_v1",
        "workflow",
    }
    assert imports <= allowed
