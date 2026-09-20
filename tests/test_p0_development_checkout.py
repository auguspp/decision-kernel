"""Temporary P0 development checkout receipt; removed before final review.

Uses only the already checked-out Git tree and existing CI diagnostic artifact.
No source/model requests, secrets, remote mutation, workflow or schedule.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess


def test_p0_exact_checkout_for_local_development():
    report = os.environ.get("CI_REPORT_DIR")
    if report is None:
        return
    root = Path(__file__).resolve().parents[1]
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
        check=True, capture_output=True, text=True, timeout=15).stdout.strip()
    assert head == os.environ["CI_CODE_SHA"]
    archive = subprocess.run(["git", "archive", "--format=zip", head], cwd=root,
        check=True, capture_output=True, timeout=45).stdout
    target = Path(report) / "p0-development-source.zip"
    with target.open("xb") as stream:
        stream.write(archive)
    receipt = {"code_sha": head, "sha256": hashlib.sha256(archive).hexdigest(),
        "bytes": len(archive), "representation": "NATIVE_GIT_ARCHIVE_EXACT_CHECKED_OUT_TREE",
        "source_requests": 0, "model_calls": 0, "remote_writes": 0}
    with (Path(report) / "p0-development-source.json").open("x") as stream:
        json.dump(receipt, stream, sort_keys=True)
