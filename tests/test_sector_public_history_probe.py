from __future__ import annotations

import json
import runpy
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github/scripts/probe-sector-public-history.py"
WORKFLOW = ROOT / ".github/workflows/sector-public-history-probe.yml"


def module():
    return runpy.run_path(str(SCRIPT))


def test_ths_parser_requires_exact_wrapper_code_and_preserves_target_fields() -> None:
    m = module()
    payload = {
        "name": "synthetic",
        "data": (
            "20260909,1,2,0.5,10.50,123,456.70,0,0,0,0;"
            "20260910,1,2,0.5,11.25,124,457.80,0,0,0,0"
        ),
    }
    text = "quotebridge_v4_line_bk_881101_01_2026(" + json.dumps(payload) + ")"
    values, meta = m["normalize_ths_text"](text, code="881101.TI", decoder=json.loads)
    assert meta["row_widths"] == [11]
    assert values["2026-09-09"] == {
        "close": Decimal("10.50"),
        "volume": Decimal("123"),
        "turnover": Decimal("456.70"),
    }
    bad = text.replace("bk_881101", "bk_884001", 1)
    try:
        m["normalize_ths_text"](bad, code="881101.TI", decoder=json.loads)
    except m["ProbeError"] as exc:
        assert "THS_IDENTITY_WRAPPER_MISMATCH" in str(exc)
    else:
        raise AssertionError("wrong wrapper identity must fail closed")


def test_compare_is_decimal_exact_and_never_grants_promotion() -> None:
    m = module()
    codes = m["CODES"]
    dates = m["TARGET_DATES"]
    fields = m["FIELDS"]
    left = {
        code: {
            day: {field: Decimal("1.0") for field in fields}
            for day in dates
        }
        for code in codes
    }
    right = {
        code: {
            day: {field: Decimal("1") for field in fields}
            for day in dates
        }
        for code in codes
    }
    rows, exact = m["compare_points"](left, right)
    assert exact is True
    assert len(rows) == 5 * 2 * 3
    right[codes[-1]][dates[-1]][fields[-1]] = Decimal("1.0001")
    _, exact = m["compare_points"](left, right)
    assert exact is False


def test_probe_scope_and_workflow_are_manual_read_only_and_secret_free() -> None:
    m = module()
    assert m["CODES"] == (
        "881101.TI", "881270.TI", "884001.TI", "884002.TI", "884023.TI"
    )
    assert m["TARGET_DATES"] == ("2026-09-09", "2026-09-10")
    assert m["FIELDS"] == ("close", "volume", "turnover")
    assert m["PUBLIC_REQUEST_MAX"] == 5
    assert m["AKSHARE_VERSION"] == "1.18.94"
    assert m["HITHINK_RUN_ID"] == 34566950303
    assert m["HITHINK_ARTIFACT_ID"] == 10187281705
    assert all(value == 0 or value is False or value == "NONE" for value in m["AUTHORITY"].values())

    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "schedule:" not in text and "push:" not in text and "pull_request:" not in text
    assert "contents: read" in text and "actions: read" in text
    assert "secrets." not in text
    assert "HITHINK_FINANCE_API_KEY" not in text and "SUB2API" not in text
    assert "artifact-ids: '10187281705'" in text
    assert "run-id: '34566950303'" in text
    assert "akshare==1.18.94" in text
    assert "github.run_attempt == 1" in text
    assert "Do not Re-run this probe" in text


def test_script_has_no_retry_loop_or_production_writer_imports() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "Retry(" not in text
    assert "HTTPAdapter(" not in text
    assert "time.sleep(" not in text
    assert "commit_research_package" not in text
    assert "save_sector" not in text
    assert "production_state_writes\": 0" in text
    assert "cache_writes\": 0" in text
    assert "events_created\": 0" in text
