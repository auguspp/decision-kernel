#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

EVIDENCE_COMMIT = "11a6f20126633ca80bfff369a0a84732825e6f23"
V2 = Path("radar_inputs/economic-company-links-livestock-v2.json")
V3 = Path("radar_inputs/economic-company-links-livestock-v3.json")
EVIDENCE = Path("radar_inputs/company-evidence/000876-newhope-business-2026-09-12.json")
LINKS = Path("radar_inputs/economic-market-links-v0.json")
CAPTURE = Path(".github/scripts/capture-stock-reading.py")


def write_json(path: Path, value: object, *, compact: bool = False) -> None:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":") if compact else None,
                      indent=None if compact else 2)
    path.write_text(text + "\n", encoding="utf-8")


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"expected exactly one replacement: {old!r}")
    return text.replace(old, new)


def main() -> None:
    now = datetime.now(timezone.utc).isoformat()
    v2 = json.loads(V2.read_text(encoding="utf-8"))
    v3 = copy.deepcopy(v2)
    v3["prepared_at"] = now
    v3["source_commit"] = EVIDENCE_COMMIT
    v3["scope_note"] = (
        "在v2五家公司基础上，只新增000876.SZ新希望。新增理由是2026-09-11保存的884278.TI畜禽饲料"
        "当前成员身份与2025年报明确饲料业务依据同时成立；不是按股价、预期通过条件或全市场排名选公司。"
        "旧v1/v2保持历史重放。"
    )
    feed = v3["nodes"][0]
    assert feed["node_id"] == "cn.livestock.price_feed"
    assert {c["ticker"] for c in feed["companies"]} == {"002714", "300498", "603477", "605296"}

    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    record = evidence["evidence_artifacts"][0]
    blob = subprocess.check_output(["git", "hash-object", str(EVIDENCE)], text=True).strip()
    feed["coverage_note"] = (
        "v2四个生猪业务案例外，新增一个当前畜禽饲料成员新希望；同一经济节点同时含生猪价与育肥猪配合饲料价。"
        "成员身份只用于路由，业务原文只证明业务存在；均不证明净受益或投资结论。"
    )
    feed["companies"].append({
        "ticker": "000876",
        "exchange": "SZSE",
        "company_name": "新希望",
        "business_scope": "2025年报业务基线：饲料、生猪养殖与屠宰；本次接入只依赖明确饲料业务存在，不把养殖链或饲料报价变化当作集团净受益。",
        "source_path": str(EVIDENCE),
        "source_blob_sha1": blob,
        "issuer_binding_note": "巨潮资讯2025年报PDF公司信息页明确000876/新希望/深圳证券交易所；业务页明确饲料业务及产品、内部与外部客户边界。",
        "exposure_size_note": "本次不提取饲料收入权重、利润弹性或2026经营刷新；内部供应与外销并存，行业饲料报价不等于公司售价、原料成本或利润。",
        "basis": [{
            "key": "business",
            "evidence_artifact_id": record["id"],
            "source_identifier": record["source_identifier"],
            "source_use": {
                "source_role": "PRIMARY_STATEMENT",
                "assertion_scope": "ATTRIBUTED_STATEMENT",
                "role_basis": "公司年报业务叙述的有限保留；只证明饲料业务存在和产品/客户边界，不是当前经营结果或净受益判断。",
            },
            "fields": [{
                "field": key,
                "label": key,
                "unit": "公司叙述",
                "kind": "TEXT",
                "scope_note": "仅限2025年报指定业务位置；不是市场输入、当前盈利或投资判断。",
            } for key in record["extracted_structured_values"]],
        }],
        "mechanisms": [
            {
                "channel": "REVENUE",
                "status": "HYPOTHESIS_WITH_RETAINED_INPUTS",
                "hypothesis": "畜禽饲料方向活跃只提示检查公司自身饲料销量、售价、产品和客户结构；内部供应与外销必须分开，不能由行业指数推导收入增长。",
                "basis_keys": ["business"],
                "next_checks": ["核对2026年公司饲料销量、售价、内外销与产品结构"],
            },
            {
                "channel": "COST",
                "status": "HYPOTHESIS_WITH_RETAINED_INPUTS",
                "hypothesis": "全国育肥猪配合饲料价格是外部观察，不是公司原料采购或制造成本；采购结构、配方、库存与地区差异仍未知。",
                "basis_keys": ["business"],
                "next_checks": ["核对原料采购、库存时滞、配方与饲料毛利口径"],
            },
            {
                "channel": "CAPACITY",
                "status": "EVIDENCE_GAP",
                "hypothesis": "业务存在不证明产能利用率或新增资本回报。",
                "basis_keys": [],
                "next_checks": ["补齐饲料产能、利用率与投产时点"],
            },
            {
                "channel": "CASH_FLOW",
                "status": "EVIDENCE_GAP",
                "hypothesis": "本次业务基线没有建立饲料业务现金兑现或集团可分配现金。",
                "basis_keys": [],
                "next_checks": ["核对经营现金流、营运资本和资本开支口径"],
            },
        ],
    })
    write_json(V3, v3, compact=True)

    links = json.loads(LINKS.read_text(encoding="utf-8"))
    link = links["links"][0]
    assert link["node_id"] == "cn.livestock.price_feed"
    assert {x["thscode"] for x in link["targets"]} == {"881102.TI", "884275.TI"}
    link["targets"].append({"family": "GRANULAR_884", "thscode": "884278.TI", "name": "畜禽饲料"})
    link["relation_note"] = (
        "人工选定的观察关联：同一国家级采集同时保存生猪、玉米与育肥猪配合饲料价格。"
        "因此除养殖业/生猪养殖外，把畜禽饲料作为并列阅读对象；这不是行业因果、成分包含、公司受益名单或盈利确认。"
        "881与884各自保留层内排名。"
    )
    link["review_question"] = (
        "生猪与饲料报价变化是否持续？对养殖公司需核对出栏、售价与成本；对饲料公司需核对自身销量、售价、原料与内外销结构。"
        "不能把行业饲料报价直接当成公司售价、成本或利润。"
    )
    links["reviewed_at"] = now
    write_json(LINKS, links)

    text = CAPTURE.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "LIVE_COMPANIES = 'radar_inputs/economic-company-links-livestock-v2.json'",
        "LEGACY_V2 = 'radar_inputs/economic-company-links-livestock-v2.json'\nLIVE_COMPANIES = 'radar_inputs/economic-company-links-livestock-v3.json'",
    )
    text = replace_once(
        text,
        "value not in {stock.COMPANY_MANIFEST, LIVE_COMPANIES}",
        "value not in {stock.COMPANY_MANIFEST, LEGACY_V2, LIVE_COMPANIES}",
    )
    text = text.replace("Never backdate v2 or silently fall back to v1.",
                        "Never backdate v2/v3 or silently fall back to an older scope.")
    CAPTURE.write_text(text, encoding="utf-8")

    t = Path("tests/test_stock_company_coverage_v2.py")
    body = t.read_text(encoding="utf-8")
    body = replace_once(
        body,
        "assert kwargs['company_manifest'] == V2 == mod['LIVE_COMPANIES']",
        "assert kwargs['company_manifest'] == mod['LIVE_COMPANIES'] == 'radar_inputs/economic-company-links-livestock-v3.json'",
    )
    body = body.replace("def test_normal_live_cli_explicitly_uses_v2_without_new_user_input",
                        "def test_normal_live_cli_explicitly_uses_current_reviewed_scope_without_new_user_input")
    t.write_text(body, encoding="utf-8")

    t2 = Path("tests/test_stock_company_next_batch_evidence.py")
    body = t2.read_text(encoding="utf-8")
    body = replace_once(body, "assert len(directions) == 3 and len(issuers) == 5",
                        "assert len(directions) == 4 and len(issuers) == 5")
    body = replace_once(body, "assert one_addition == 25 <= stock.MAX_REQUESTS == 26",
                        "assert one_addition == 26 <= stock.MAX_REQUESTS == 26")
    body = replace_once(body, "assert two_additions == 28 > stock.MAX_REQUESTS",
                        "assert two_additions == 29 > stock.MAX_REQUESTS")
    t2.write_text(body, encoding="utf-8")

    test = Path("tests/test_stock_company_coverage_v3.py")
    test.write_text('''"""One current feed-member company closes the demonstrated 2026-09-11 coverage gap."""\nimport hashlib\nimport json\nfrom datetime import datetime\nfrom pathlib import Path\n\nfrom decision_kernel.evidence import EvidenceArtifact\nfrom decision_kernel.identity import canonical_hash\nfrom decision_kernel.runtime import stock_radar_reading as stock\n\nROOT = Path(__file__).resolve().parents[1]\nV2 = "radar_inputs/economic-company-links-livestock-v2.json"\nV3 = "radar_inputs/economic-company-links-livestock-v3.json"\nEVIDENCE = "radar_inputs/company-evidence/000876-newhope-business-2026-09-12.json"\n\n\ndef test_v3_is_append_only_over_v2_and_binds_newhope_evidence():\n    old = json.loads((ROOT/V2).read_bytes())\n    new = json.loads((ROOT/V3).read_bytes())\n    assert new["nodes"][1] == old["nodes"][1]\n    assert new["nodes"][0]["companies"][:-1] == old["nodes"][0]["companies"]\n    company = new["nodes"][0]["companies"][-1]\n    assert (company["ticker"], company["exchange"], company["company_name"]) == ("000876", "SZSE", "新希望")\n    raw = (ROOT/EVIDENCE).read_bytes()\n    assert hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\\0"+raw).hexdigest() == company["source_blob_sha1"]\n    source = json.loads(raw)\n    evidence = EvidenceArtifact.model_validate(source["evidence_artifacts"][0])\n    assert evidence.source_identifier == "NEWHOPE:000876:2025-ANNUAL:business"\n    assert evidence.report_period_end.isoformat() == "2025-12-31"\n    assert evidence.retention_mode.value == "EXTRACTED_VALUES"\n    assert evidence.replayability_level.value == "PARTIAL" and evidence.raw_storage_ref is None\n    record = source["evidence_artifacts"][0]\n    assert record["content_hash"] == canonical_hash({k:record[k] for k in ("source_locator","source_location","extracted_structured_values")})\n    assert evidence.retrieved_at == datetime.fromisoformat(source["recorded_at"])\n    assert evidence.retrieved_at > datetime.fromisoformat(old["prepared_at"])\n    assert new["source_commit"] == "11a6f20126633ca80bfff369a0a84732825e6f23"\n\n\ndef test_existing_livestock_economic_node_adds_only_reviewed_feed_target():\n    links = json.loads((ROOT/"radar_inputs/economic-market-links-v0.json").read_bytes())\n    link = next(x for x in links["links"] if x["node_id"] == "cn.livestock.price_feed")\n    targets = {(x["family"], x["thscode"], x["name"]) for x in link["targets"]}\n    assert targets == {\n        ("BROAD_881", "881102.TI", "养殖业"),\n        ("GRANULAR_884", "884275.TI", "生猪养殖"),\n        ("GRANULAR_884", "884278.TI", "畜禽饲料"),\n    }\n    assert "公司售价、成本或利润" in link["review_question"]\n\n\ndef test_v3_worst_case_reservation_hits_but_does_not_raise_existing_ceiling():\n    spec = json.loads((ROOT/V3).read_bytes())\n    links = json.loads((ROOT/"radar_inputs/economic-market-links-v0.json").read_bytes())\n    covered = {n["node_id"] for n in spec["nodes"] if n["companies"]}\n    directions = {t["thscode"] for link in links["links"] if link["node_id"] in covered for t in link["targets"]}\n    issuers = {(c["ticker"], c["exchange"]) for n in spec["nodes"] for c in n["companies"]}\n    assert len(directions) == 4 and len(issuers) == 6\n    assert 4 + len(directions) + 3*len(issuers) == stock.MAX_REQUESTS == 26\n\n\ndef test_live_scope_is_v3_while_v2_remains_explicitly_accepted():\n    import runpy\n    mod = runpy.run_path(str(ROOT/".github/scripts/capture-stock-reading.py"), run_name="coverage_v3_test")\n    assert mod["LIVE_COMPANIES"] == V3 and mod["LEGACY_V2"] == V2\n    assert mod["company_scope"](V2) == V2\n    assert mod["company_scope"](V3) == V3\n''', encoding="utf-8")

    doc = Path("docs/stock-company-coverage-newhope-2026-09-12.md")
    doc.write_text(f'''# P0 Stock business coverage — New Hope feed bridge — 2026-09-12\n\nStatus: bounded implementation/evidence change; **not a recommendation, Research route, Odds, Action or natural-schedule acceptance**.\n\nThe Human-authorized demo run `34658920384` successfully completed the Stock read/replay chain for market session 2026-09-11 but produced `BUSINESS_COVERAGE_INSUFFICIENT`, with zero planned issuers. The saved Sector artifact for that session shows `884278.TI 畜禽饲料` gate-active and its retained exact membership includes `000876.SZ 新希望`. This patch closes only that demonstrated gap.\n\nReuse first: `cn.livestock.price_feed` already retains national pig, corn and fattening-pig compound-feed observations, so no new economic node/provider/schema/selector is introduced. The reviewed link adds only `884278.TI`; it explicitly does not mean feed-index movement equals a company's selling price, cost or profit.\n\nNew Hope evidence is a limited extraction from the CNINFO-hosted 2025 annual report (`1225251161.PDF`). The company information binds 新希望 / 000876 / 深圳证券交易所; the business section states feed is a core business and describes premix, concentrate and compound feed across poultry, pig, aquatic and ruminant categories. Only business existence and customer/product boundaries are retained. Original PDF bytes are not stored in GitHub.\n\nProduction v3 inherits v2 unchanged and appends only New Hope. Old v1/v2 remain explicit replay scopes. Worst-case existing reservation is `4 + 4 directions + 3×6 issuers = 26`, exactly the existing limit; no second issuer, request ceiling increase or timeout change is included.\n\nEvidence source commit: `{EVIDENCE_COMMIT}`.\n\nA future fresh Stock demo must still bind a qualified Sector state and pass shared-Key preflight. Success can still yield no surfaced stock if New Hope fails price/data conditions. Evidence changes Belief; Price changes Odds; this patch creates neither investment authority nor a buy recommendation.\n''', encoding="utf-8")


if __name__ == "__main__":
    main()
