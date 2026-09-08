"""Exercise the existing CLI from a fresh base-only install, outside the checkout.

No external research, market/provider calls, candidate writes, or registry changes occur.
Only the project's already declared base packaging dependencies may be downloaded by pip.
"""
from __future__ import annotations

import json
from pathlib import Path
import runpy
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE = "decision_kernel.runtime.external_research_execution"


def _run(command: list[str], *, cwd: Path, timeout: int = 180) -> str:
    completed = subprocess.run(
        command, cwd=cwd, text=True, capture_output=True, timeout=timeout,
        check=False,
    )
    assert completed.returncode == 0, (
        f"command failed ({completed.returncode}): {command!r}\n"
        f"{completed.stdout}\n{completed.stderr}"
    )
    return completed.stdout


def test_external_research_cli_in_actual_base_only_install(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Install the real package without dev/feeds and execute schema + validation."""
    environment = tmp_path / "base-only"
    _run([sys.executable, "-I", "-m", "venv", str(environment)], cwd=tmp_path)
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    # -I prevents PYTHONPATH/user-site leakage; cwd is not the source checkout.
    _run([
        str(python), "-I", "-m", "pip", "--isolated", "install",
        "--disable-pip-version-check", "--no-cache-dir", "--retries", "0",
        "--timeout", "30", str(ROOT),
    ], cwd=tmp_path)
    inventory = json.loads(_run([
        str(python), "-I", "-c",
        "import importlib.metadata as m,json; "
        "print(json.dumps({d.metadata['Name'].lower(): d.version for d in m.distributions()}))",
    ], cwd=tmp_path))
    assert inventory["decision-kernel"] == "0.1.0"
    assert inventory["pydantic"] == "2.13.4"
    assert not {"pytest", "requests", "feedparser", "beautifulsoup4", "pyarrow", "pypdf"} & inventory.keys()
    schema_file = tmp_path / "schema.json"
    _run([str(python), "-I", "-m", MODULE, "schema", "--output", str(schema_file)], cwd=tmp_path)
    schemas = json.loads(schema_file.read_text(encoding="utf-8"))
    assert set(schemas) == {
        "ExternalResearchInputPacket", "ExternalResearchCandidate", "DiscoveryInput",
        "PreResearchResult", "QuickResearchResult", "EvidenceArtifact", "ResearchFunnelResult",
    }
    # Reuse the existing explicit synthetic fixtures in the parent test process.
    # The clean child neither imports pytest nor loads tests from the checkout.
    fixtures = runpy.run_path(str(ROOT / "tests/test_external_research_execution.py"))
    packet = fixtures["packet"]()
    candidate = fixtures["complete_candidate"](packet)
    input_path, candidate_path = tmp_path / "input.json", tmp_path / "candidate.json"
    input_path.write_text(packet.model_dump_json(), encoding="utf-8")
    candidate_path.write_text(candidate.model_dump_json(), encoding="utf-8")
    result_path = tmp_path / "validation.json"
    validation_log = _run([
        str(python), "-I", "-m", MODULE, "validate", "--input", str(input_path),
        "--candidate", str(candidate_path), "--output", str(result_path),
    ], cwd=tmp_path)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    expected = fixtures["validate_external_research_candidate"](packet=packet, candidate=candidate)
    assert result["status"] == "VALIDATED_FUNNEL_RESULT"
    assert result["funnel_result"] == expected.funnel_result.model_dump(mode="json")
    assert result["validation_hash"] == fixtures["canonical_hash"](expected)
    # Explicit machine-readable log, rather than treating an import-name grep as runtime proof.
    with capsys.disabled():
        print("P0_4A_BASE_ONLY_INSTALL=" + json.dumps(inventory, sort_keys=True), flush=True)
        print("P0_4A_BASE_ONLY_SCHEMA=PASS", flush=True)
        print("P0_4A_BASE_ONLY_SYNTHETIC_FUNNEL=PASS", flush=True)
        print(validation_log, flush=True)
