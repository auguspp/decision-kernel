"""One current feed-member company closes the demonstrated 2026-09-11 coverage gap."""
import hashlib
import json
from datetime import datetime
from pathlib import Path

from decision_kernel.evidence import EvidenceArtifact
from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import stock_radar_reading as stock

ROOT = Path(__file__).resolve().parents[1]
V2 = "radar_inputs/economic-company-links-livestock-v2.json"
V3 = "radar_inputs/economic-company-links-livestock-v3.json"
EVIDENCE = "radar_inputs/company-evidence/000876-newhope-business-2026-09-12.json"


def test_v3_is_append_only_over_v2_and_binds_newhope_evidence():
    old = json.loads((ROOT/V2).read_bytes())
    new = json.loads((ROOT/V3).read_bytes())
    assert new["nodes"][1] == old["nodes"][1]
    assert new["nodes"][0]["companies"][:-1] == old["nodes"][0]["companies"]
    company = new["nodes"][0]["companies"][-1]
    assert (company["ticker"], company["exchange"], company["company_name"]) == ("000876", "SZSE", "新希望")
    raw = (ROOT/EVIDENCE).read_bytes()
    assert hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest() == company["source_blob_sha1"]
    source = json.loads(raw)
    evidence = EvidenceArtifact.model_validate(source["evidence_artifacts"][0])
    assert evidence.source_identifier == "NEWHOPE:000876:2025-ANNUAL:business"
    assert evidence.report_period_end.isoformat() == "2025-12-31"
    assert evidence.retention_mode.value == "EXTRACTED_VALUES"
    assert evidence.replayability_level.value == "PARTIAL" and evidence.raw_storage_ref is None
    record = source["evidence_artifacts"][0]
    assert record["content_hash"] == canonical_hash({k:record[k] for k in ("source_locator","source_location","extracted_structured_values")})
    assert evidence.retrieved_at == datetime.fromisoformat(source["recorded_at"])
    assert evidence.retrieved_at > datetime.fromisoformat(old["prepared_at"])
    assert new["source_commit"] == "11a6f20126633ca80bfff369a0a84732825e6f23"


def test_existing_livestock_economic_node_adds_only_reviewed_feed_target():
    links = json.loads((ROOT/"radar_inputs/economic-market-links-v0.json").read_bytes())
    link = next(x for x in links["links"] if x["node_id"] == "cn.livestock.price_feed")
    targets = {(x["family"], x["thscode"], x["name"]) for x in link["targets"]}
    assert targets == {
        ("BROAD_881", "881102.TI", "养殖业"),
        ("GRANULAR_884", "884275.TI", "生猪养殖"),
        ("GRANULAR_884", "884278.TI", "畜禽饲料"),
    }
    assert "公司售价、成本或利润" in link["review_question"]


def test_v3_worst_case_reservation_hits_but_does_not_raise_existing_ceiling():
    spec = json.loads((ROOT/V3).read_bytes())
    links = json.loads((ROOT/"radar_inputs/economic-market-links-v0.json").read_bytes())
    covered = {n["node_id"] for n in spec["nodes"] if n["companies"]}
    directions = {t["thscode"] for link in links["links"] if link["node_id"] in covered for t in link["targets"]}
    issuers = {(c["ticker"], c["exchange"]) for n in spec["nodes"] for c in n["companies"]}
    assert len(directions) == 4 and len(issuers) == 6
    assert 4 + len(directions) + 3*len(issuers) == stock.MAX_REQUESTS == 26


def test_live_scope_is_v3_while_v2_remains_explicitly_accepted():
    import runpy
    mod = runpy.run_path(str(ROOT/".github/scripts/capture-stock-reading.py"), run_name="coverage_v3_test")
    assert mod["LIVE_COMPANIES"] == V3 and mod["LEGACY_V2"] == V2
    assert mod["company_scope"](V2) == V2
    assert mod["company_scope"](V3) == V3
