"""Synthetic capacity/qualification checks; no source calls or production records."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import odds_watch

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 30, 14, 0, tzinfo=timezone.utc)


def inputs():
    return (odds_watch.load_json(ROOT / "decision_inputs/odds-watch-v0.json"),
            odds_watch.load_json(ROOT / "current_state/registry.json"))


def expanded(size, *, price_entries=False):
    config, registry = inputs()
    price_template = deepcopy(next(c for c in config["active_cases"] if c["ticker"] == "601155.SH"))
    price_source = deepcopy(next(r for r in registry["references"] if r["id"] == price_template["registry_reference_id"]))
    evidence_source = deepcopy(next(r for r in registry["references"] if r["id"] == "c-longitudinal-xingsen-20260930"))
    evidence_template = {
        "ticker": "899999.SZ",
        "company_name": "Synthetic evidence-only template",
        "registry_reference_id": evidence_source["id"],
        "recompute_route": "EVIDENCE_REOPEN_RESEARCH_REVIEW_NOT_PRICE_TRIGGER",
        "prerequisite": "Synthetic test reopen condition only.",
        "conditions": [],
        "odds_level": "L0_NO_ODDS",
        "boundary_authority": "NONE",
        "watch_mode": "EVIDENCE_REOPEN",
        "boundary_source_path": None,
        "boundary_source_ref": None,
    }
    additions = size - len(config["active_cases"])
    for n in range(additions):
        evidence_only = (n == 0) or not price_entries
        template = evidence_template if evidence_only else price_template
        source = evidence_source if evidence_only else price_source
        ticker, ref_id = f"{800000 + n:06d}.SZ", f"synthetic-capacity-{n}"
        row = deepcopy(template)
        row.update(ticker=ticker, company_name=f"Synthetic fixture {n}", registry_reference_id=ref_id)
        ref = deepcopy(source)
        ref.update(id=ref_id, case=ticker)
        config["active_cases"].append(row)
        registry["references"].append(ref)
    return config, registry

def build(config, registry, *, unavailable=None):
    calls = []

    def fetch_market(*, thscode, observed_at):
        calls.append(thscode)
        if thscode == unavailable:
            raise RuntimeError("synthetic price gap")
        return SimpleNamespace(market_price="1000", market_timestamp=NOW,
                               market_data_source="SYNTHETIC_TEST_ONLY",
                               price_convention="raw_close", currency="CNY")

    result = odds_watch.build_watch(config=config, registry=registry, observed_at=NOW,
                                   fetch_market=fetch_market, price_error_types=(RuntimeError,))
    return result, calls


def reseal(report):
    report["watch_hash"] = canonical_hash(report["watch"])
    return report


@pytest.mark.parametrize("size,price_entries", [(20, False), (24, False), (20, True), (24, True)])
def test_wider_mixed_watch_retains_every_case_and_separates_price_gap_from_evidence(size, price_entries):
    config, registry = expanded(size, price_entries=price_entries)
    result, calls = build(config, registry, unavailable="600598.SH")
    odds_watch.validate_report(result)
    watch = result["watch"]
    price_count = size - 1 if price_entries else 7
    assert len(watch["active_cases"]) == watch["active_case_count"] == size
    assert len(calls) == price_count
    assert watch["price_evaluated_case_count"] == price_count - 1
    assert watch["price_gap_count"] == 1
    assert watch["evidence_only_case_count"] == size - price_count
    assert watch["attention_case_count"] == 0
    if not price_entries:
        assert all(not c.startswith("8") for c in calls)
    text = odds_watch.render_markdown(result)
    assert f"活跃观察：{size}" in text
    assert f"价格已判断：{price_count - 1}" in text
    assert "未自动判断新证据是否满足" in text


def test_guardrail_rejects_before_source_work_rather_than_silently_slicing_the_list():
    config, registry = expanded(25)

    def forbidden(**kwargs):
        pytest.fail("over-bound configuration must not start market work")

    with pytest.raises(ValueError, match="outside bounded scope"):
        odds_watch.build_watch(config=config, registry=registry, observed_at=NOW, fetch_market=forbidden)
    assert len(config["active_cases"]) == 25


@pytest.mark.parametrize("mutation", [
    {"boundary_authority": "HUMAN_ACCEPTED_ODDS"},
    {"odds_level": "L4_HUMAN_DECISION_BOUNDARY"},
    {"recompute_route": "PRICE_ONLY_RECOMPUTE_ELIGIBLE_ONLY_IF_FROZEN_BELIEF_AND_METHOD_STILL_VALID"},
    {"boundary_source_path": None, "boundary_source_ref": None},
    {"boundary_source_ref": "main"},
    {"boundary_source_path": "../arbitrary.md"},
])
def test_analyst_price_boundary_cannot_gain_human_authority_or_lose_exact_source(mutation):
    config, registry = inputs()
    row = next(c for c in config["active_cases"] if c["ticker"] == "601155.SH")
    row.update(mutation)
    with pytest.raises(ValueError):
        odds_watch.validate_config(config, registry)


def test_l1_is_supported_without_upgrading_the_underlying_result_or_human_acceptance():
    config, registry = inputs()
    row = next(c for c in config["active_cases"] if c["ticker"] == "601155.SH")
    row["odds_level"] = "L1_ANALYST_SENSITIVITY"
    report, _ = build(config, registry)
    odds_watch.validate_report(report)
    saved = next(c for c in report["watch"]["active_cases"] if c["ticker"] == "601155.SH")
    assert saved["odds_level"] == "L1_ANALYST_SENSITIVITY"
    assert saved["boundary_authority"] == "ANALYST_DERIVED"


@pytest.mark.parametrize("kind", ["missing_grade", "invented_acceptance", "wrong_count", "evidence_with_price"])
def test_resealed_report_still_has_to_preserve_qualification_and_complete_coverage(kind):
    config, registry = expanded(8, price_entries=False) if kind == "evidence_with_price" else inputs()
    report, _ = build(config, registry)
    watch = report["watch"]
    rows = {c["ticker"]: c for c in watch["active_cases"]}
    if kind == "missing_grade":
        del rows["601155.SH"]["odds_level"]
    elif kind == "invented_acceptance":
        rows["601155.SH"]["boundary_authority"] = "HUMAN_DECISION"
    elif kind == "wrong_count":
        watch["price_evaluated_case_count"] = 999
    else:
        evidence = next(c for c in watch["active_cases"] if c.get("watch_mode") == "EVIDENCE_REOPEN")
        evidence["price"] = "1"
    with pytest.raises(ValueError):
        odds_watch.validate_report(reseal(report))


def test_legacy_ungraded_price_report_remains_readable_without_fabricated_zero_coverage():
    config, registry = inputs()
    report, _ = build(config, registry)
    watch = report["watch"]
    watch["active_cases"] = [c for c in watch["active_cases"] if c["watch_mode"] == "PRICE_CONDITION"]
    watch["active_case_count"] = 7
    del watch["price_evaluated_case_count"]
    del watch["evidence_only_case_count"]
    for row in watch["active_cases"]:
        for key in ("odds_level", "boundary_authority", "watch_mode", "boundary_source", "price_fetch_performed"):
            row.pop(key)
    odds_watch.validate_report(reseal(report))
    assert "价格已判断：7" in odds_watch.render_markdown(report)
    assert all("odds_level" not in row for row in watch["active_cases"])
