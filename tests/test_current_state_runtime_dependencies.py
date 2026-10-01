"""Publisher installs existing runtime extras, never relying on a dev environment."""
import ast
from pathlib import Path
import tomllib


def test_publisher_installs_existing_runtime_extra_instead_of_dev_environment():
    project = tomllib.loads(Path("pyproject.toml").read_text())
    dependencies = project["project"]["optional-dependencies"]["feeds"]
    assert "requests==2.34.2" in dependencies
    documents = project["project"]["optional-dependencies"]["documents"]
    assert any(d.startswith("pypdf==") for d in documents)
    concept = project["project"]["optional-dependencies"]["concept"]
    assert concept == ["eltdx==3.2.2"]
    assert concept[0] in project["project"]["optional-dependencies"]["dev"]
    assert not any(d.startswith("eltdx") for d in project["project"]["dependencies"])
    workflow = Path(".github/workflows/current-state-read-entry.yml").read_text()
    assert "python -m pip install -e '.[feeds,documents,concept]'" in workflow
    assert ".[dev]" not in workflow
    assert "cron: '50 23 * * *'" in workflow and "cron: '10 11 * * *'" in workflow
    assert "workflow_dispatch:" not in workflow


def test_existing_requests_dependency_is_only_used_by_github_delivery_client():
    module = ast.parse(Path("src/decision_kernel/runtime/current_state_delivery.py").read_text())
    imports = [alias.name for node in ast.walk(module) if isinstance(node, ast.Import) for alias in node.names]
    assert "requests" in imports
    source = Path("src/decision_kernel/runtime/current_state_delivery.py").read_text()
    assert 'self.root = "https://api.github.com/repos/"' in source
    assert "run_live_package" not in source and "run_research_workflow" not in source
