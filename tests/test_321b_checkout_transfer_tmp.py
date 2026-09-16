"""Temporary CI-only source transfer, removed before the implementation merge.

The local workspace cannot resolve GitHub. Export only tracked Git objects via
native git archive into the existing CI diagnostics, never credentials or runtime
state. This is engineering transport evidence, not Research or market authority.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import tarfile


def test_exact_tracked_source_archive(tmp_path):
    root = Path(__file__).resolve().parents[1]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    assert head == os.environ.get("CI_CODE_SHA", head)
    out = Path(os.environ.get("CI_REPORT_DIR", str(tmp_path)))
    archive = out / "321b-checkout.tar"
    subprocess.run(["git", "archive", "--format=tar", "--output", str(archive), head],
                   cwd=root, check=True, timeout=30)
    inventory = subprocess.check_output(["git", "ls-tree", "-r", "--full-tree", head], cwd=root)
    (out / "321b-checkout-tree.txt").write_bytes(inventory)
    with tarfile.open(archive) as saved:
        names = {m.name for m in saved if not m.isdir()}
    assert names == {line.split(b"\t", 1)[1].decode() for line in inventory.splitlines()}
    (out / "321b-checkout.json").write_text(json.dumps({
        "code_commit": head,
        "baseline_commit": "2f38a62614a0f6da135b1467c087ba3cd62b0d0f",
        "baseline_tree": "784081e270e0cd792f5c67260f8fa10d3cf954ca",
        "temporary_path": "tests/test_321b_checkout_transfer_tmp.py",
        "bytes": archive.stat().st_size,
        "sha256": sha256(archive.read_bytes()).hexdigest(),
        "inventory_sha256": sha256(inventory).hexdigest(),
        "semantics": "NATIVE_TRACKED_GIT_SOURCE_NOT_PRODUCTION_STATE",
    }, sort_keys=True) + "\n", encoding="utf-8")
