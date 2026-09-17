"""Temporary exact-tree diagnostic; remove before final #413 review."""
from hashlib import sha256
import json
import os
from pathlib import Path
import socket
import subprocess


def test_export_exact_git_tree_for_offline_acceptance(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Git archive diagnostics cannot request network")

    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    root = Path(__file__).resolve().parents[1]
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True, timeout=10,
    ).stdout.strip()
    assert head == os.environ["CI_CODE_SHA"]
    tree = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"], cwd=root, check=True,
        capture_output=True, text=True, timeout=10,
    ).stdout.strip()
    output = Path(os.environ["CI_REPORT_DIR"]) / "exact-git-tree-diagnostic"
    output.mkdir(parents=True, exist_ok=False)
    archive = output / "repository.tar.gz"
    subprocess.run(
        ["git", "archive", "--format=tar.gz", "--output", str(archive), head],
        cwd=root, check=True, timeout=30,
    )
    inventory = subprocess.run(
        ["git", "ls-tree", "-r", "-z", head], cwd=root, check=True,
        capture_output=True, timeout=10,
    ).stdout
    (output / "git-ls-tree.bin").write_bytes(inventory)
    (output / "identity.json").write_text(json.dumps({
        "repository": "auguspp/decision-kernel",
        "code_sha": head,
        "tree_sha": tree,
        "archive_sha256": sha256(archive.read_bytes()).hexdigest(),
        "inventory_sha256": sha256(inventory).hexdigest(),
        "semantics": "EXACT_NATIVE_GIT_ARCHIVE_DIAGNOSTIC_NOT_RESEARCH_OR_PUBLICATION",
        "network_calls": 0,
        "investment_authority": "NONE",
    }, sort_keys=True) + "\n", encoding="utf-8")
    assert archive.stat().st_size > 0
