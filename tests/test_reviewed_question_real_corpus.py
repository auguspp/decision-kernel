"""Fixed real source bytes, not new Research or live market qualification."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket

from decision_kernel.runtime.current_state import validate_read_package

ROOT = Path(__file__).parent / "fixtures" / "reviewed_question_real"
R = "ead15d17e82f9487f76e78194b465331b64bb87d"
M = "9fb100ac330d06a3448c4ddf2a16fa12fbe6abae"


def test_real_saved_reading_and_origin_bytes(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("real-corpus replay cannot use the network")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    expected = {
        "reading.json": (185688, "1060a6f8f1da49e2cb4ce1fb07763c9de23e51ab"),
        "origin.json": (72255, "2e9af24b340531d9a98f93836798a788c5d5ae71"),
    }
    manifest = {}
    for name, (size, blob) in expected.items():
        raw = (ROOT / name).read_bytes()
        assert len(raw) == size
        assert hashlib.sha1(b"blob " + str(size).encode() + b"\0" + raw).hexdigest() == blob
        manifest[name] = {"bytes": size, "git_blob": blob, "sha256": hashlib.sha256(raw).hexdigest()}
    reading = json.loads((ROOT / "reading.json").read_bytes())
    validate_read_package(reading)
    assert reading["code_commit"] == M
    assert reading["reading_hash"] == "9df13bff2394152c5668a3f3d83cf2b1c9c01d47f67a16c1696d7fa4f449a790"
    origin = json.loads((ROOT / "origin.json").read_bytes())
    rows = origin["projection"]["all_stock_observations"]
    selected = [row for row in rows if row["thscode"] == "300711.SZ"]
    assert len(selected) == 1
    assert selected[0]["status"] == "CONTRACT_CHECKED_RAW_READING"
    assert selected[0]["business_benefit_status"] == "NOT_ESTABLISHED"
    # Existing CI diagnostics only. Preserve actual original bytes, never fabricate a reading.
    directory = os.environ.get("CI_REPORT_DIR")
    if directory:
        output = Path(directory) / "reviewed-question-real"
        output.mkdir(exist_ok=False)
        for name in expected:
            (output / name).write_bytes((ROOT / name).read_bytes())
        (output / "source-readback.json").write_text(json.dumps({
            "meaning": "EXACT_SAVED_SOURCE_BYTES_NOT_QUESTION_PREPARATION_OR_RESEARCH",
            "reading_commit": R, "code_commit": M, "files": manifest,
            "network_calls": 0, "research_executed": False,
        }, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
