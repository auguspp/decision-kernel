"""Frozen real input replay, not new Research or live market/admission checks."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import socket

import pytest
from decision_kernel.runtime.current_state import validate_read_package
from decision_kernel.runtime import reviewed_question_input as question
from decision_kernel.runtime.external_research_admission import AdmissionRejected

ROOT = Path(__file__).parent / "fixtures" / "reviewed_question_real"
R = "ead15d17e82f9487f76e78194b465331b64bb87d"
M = "9fb100ac330d06a3448c4ddf2a16fa12fbe6abae"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("real-corpus replay cannot use the network")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


def test_real_saved_reading_and_origin_bytes():
    expected = {
        "reading.json": (185688, "1060a6f8f1da49e2cb4ce1fb07763c9de23e51ab"),
        "origin.json": (72255, "2e9af24b340531d9a98f93836798a788c5d5ae71"),
    }
    for name, (size, blob) in expected.items():
        raw = (ROOT / name).read_bytes()
        assert len(raw) == size
        assert hashlib.sha1(b"blob " + str(size).encode() + b"\0" + raw).hexdigest() == blob
    reading = json.loads((ROOT / "reading.json").read_bytes())
    validate_read_package(reading)
    assert reading["code_commit"] == M
    assert reading["reading_hash"] == "9df13bff2394152c5668a3f3d83cf2b1c9c01d47f67a16c1696d7fa4f449a790"
    origin = json.loads((ROOT / "origin.json").read_bytes())
    selected = [row for row in origin["projection"]["all_stock_observations"]
                if row["thscode"] == "300711.SZ"]
    assert len(selected) == 1
    assert selected[0]["status"] == "CONTRACT_CHECKED_RAW_READING"
    assert selected[0]["business_benefit_status"] == "NOT_ESTABLISHED"


def replay_checks():
    case = json.loads((ROOT / "case.json").read_bytes())
    files = {}
    for row in case["source_files"]:
        rel = PurePosixPath(row["fixture_path"])
        assert not rel.is_absolute() and ".." not in rel.parts
        assert rel.parts[0] == "fixtures"
        path = Path(__file__).parent / str(rel)
        assert not path.is_symlink()
        raw = path.read_bytes()
        assert len(raw) <= 512 * 1024
        assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == row["git_blob"]
        assert hashlib.sha256(raw).hexdigest() == row["sha256"]
        key = (row["ref"], row["path"])
        assert key not in files
        files[key] = raw
    return case, dict(
        question_source=case["question_source"], input_raw=(ROOT / "input.json").read_bytes(),
        preflight_raw=(ROOT / "source-preflight.json").read_bytes(),
        catalog_source=case["catalog_source"],
        load=lambda spec: files[(spec["ref"], spec["path"])],
        commit=lambda ref: copy.deepcopy(case["commit_metadata"][ref]),
        checked_at=case["checked_at"], current_code=lambda: case["current_code"],
    )


def test_real_declared_question_uses_complete_original_prepare():
    case, checks = replay_checks()
    result = question.prepare(**checks)  # Original gate/model/reading validation; not mocked.
    assert result == json.loads((ROOT / "prepare-receipt.json").read_bytes())
    assert result["execution_key"] == case["expected_execution_key"]
    assert result["status"] == "QUESTION_INPUT_PREPARED_NOT_EXECUTED"
    assert result["research_execution_allowed"] is False
    assert result["formal_research_budget_used"] == result["remote_writes"] == 0
    assert result["funnel_invoked"] is False
    # Keep both unrelated historical identities; never manufacture an empty catalogue.
    catalog = json.loads((ROOT / "catalog.json").read_bytes())
    assert len(catalog["inputs"]) == 2
    assert len({x["execution_id"] for x in catalog["inputs"]}) == 1
    assert len({x["canonical_input_hash"] for x in catalog["inputs"]}) == 2
    directory = os.environ.get("CI_REPORT_DIR")
    if directory:
        output = Path(directory) / "reviewed-question-real"
        output.mkdir(exist_ok=False)
        for path in ROOT.iterdir():
            assert path.is_file() and not path.is_symlink()
            (output / path.name).write_bytes(path.read_bytes())
        (output / "replayed-prepare.json").write_text(json.dumps({
            "meaning": "FIXED_REAL_INPUT_REPLAY_NOT_LIVE_ADMISSION_OR_RESEARCH",
            "original_checked_at": case["checked_at"], "receipt": result,
            "network_calls": 0, "original_pdf_reparsed_by_ci": False,
        }, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def test_real_input_missing_required_body_still_rejected():
    _, checks = replay_checks()
    preflight = json.loads(checks["preflight_raw"])
    preflight["required_classes"][0]["body_ids"] = []
    checks["preflight_raw"] = json.dumps(preflight, ensure_ascii=False).encode()
    with pytest.raises(AdmissionRejected) as failure:
        question.prepare(**checks)
    assert failure.value.code == "SOURCE_PREFLIGHT_INCOMPLETE"
