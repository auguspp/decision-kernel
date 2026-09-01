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
