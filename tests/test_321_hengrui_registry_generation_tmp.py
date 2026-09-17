"""TEMP: emit exact paired Hengrui registry bytes for #321 Acceptance 6."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "current_state/registry.json"
DATA_REF = "4755d25e63dfe5d91f31d514342e4cc0f16115a2"
RESEARCH_ID = "600276-hengrui-research-commit-20260917"
ODDS_ID = "600276-hengrui-human-price-conditional-odds-20260917"

RESEARCH = (
    '    {"id":"600276-hengrui-research-commit-20260917","case":"600276.SH","use":"RETAINED_RESEARCH_PACKAGE",'
    '"purpose_note":"#321 Acceptance 6 historical Human-origin migration: freezes the retained final Round3 Hengrui Belief into schema-v2 COMMITTED Research without ValuationBasis, numerical Scenario or probability. model_risk remains NOT_ESTABLISHED; retained Git migration records prove historical declarations, not current company-source truth. No Market/canonical Odds, Human acceptance, Action/watch or Investment Authority is established by this commit operation.",'
    '"source":{"path":"docs/readings/600276-hengrui-research-commit-2026-09-17/commit.json","ref":"4755d25e63dfe5d91f31d514342e4cc0f16115a2","git_blob":"a3147841eeacb65c8cb4d4827bb7082e95bb6f63"},'
    '"archive":{"format":"RESEARCH_COMMIT","snapshot_id":"ea9b4e56-c998-5dcd-b8fa-3f1539612762"}},\n'
)
ODDS = (
    '    {"id":"600276-hengrui-human-price-conditional-odds-20260917","case":"600276.SH","use":"HISTORICAL_PROVISIONAL_ODDS_CHECKPOINT",'
    '"purpose_note":"#321 Acceptance 6 typed Human-price round-trip: exact retained 42.93 CNY HUMAN_SUPPLIED_PROVISIONAL_PRICE / CONTEXT_ONLY is evaluated against the later frozen Research as PRE_RESEARCH_RETROSPECTIVE_REFERENCE_NOT_PIT. Four legacy terminal-value ranges are represented only by their eight lower/upper endpoints; no midpoint and no old 30/50/20 probability is revived. Cardinal probability/weighted aggregate, Market qualification, canonical Odds, Human acceptance by this operation, Action/watch and Investment Authority remain NOT_ESTABLISHED/NONE.",'
    '"source":{"path":"docs/readings/600276-hengrui-conditional-odds-2026-09-17/result.json","ref":"4755d25e63dfe5d91f31d514342e4cc0f16115a2","git_blob":"764132afe2a69514a7d620fc9207cb2497598022"},'
    '"archive":{"format":"ODDS_RESULT","result_kind":"CONDITIONAL_PROVISIONAL","research_record_id":"600276-hengrui-research-commit-20260917","research_snapshot_hash":"c001d697620b6a547857832694af289239ad1f1a10bde62fa2e5a70373898dad"}},\n'
)


def test_emit_exact_paired_registry_bytes():
    raw = REGISTRY.read_text(encoding="utf-8")
    assert RESEARCH_ID not in raw and ODDS_ID not in raw
    needle = '    {"id":"odds-hengrui-human"'
    assert raw.count(needle) == 1
    updated = raw.replace(needle, RESEARCH + ODDS + needle, 1)
    parsed = json.loads(updated)
    records = {item["id"]: item for item in parsed["references"]}
    assert records[RESEARCH_ID]["source"]["ref"] == DATA_REF
    assert records[ODDS_ID]["archive"] == {
        "format": "ODDS_RESULT",
        "result_kind": "CONDITIONAL_PROVISIONAL",
        "research_record_id": RESEARCH_ID,
        "research_snapshot_hash": "c001d697620b6a547857832694af289239ad1f1a10bde62fa2e5a70373898dad",
    }
    out = Path(os.environ["CI_REPORT_DIR"]) / "hengrui-acceptance6-final"
    out.mkdir(parents=True, exist_ok=False)
    (out / "registry.json").write_text(updated, encoding="utf-8")
