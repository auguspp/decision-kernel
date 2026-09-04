from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime.sector_radar_state import (
    parse_sector_radar_market_state,
)


BOOTSTRAP = Path("radar_inputs/sector-radar-state-bootstrap-2026-09-04.json.gz")
MANIFEST = Path(
    "radar_inputs/sector-radar-state-bootstrap-2026-09-04.manifest.json"
)


def test_durable_sector_radar_state_bootstrap_matches_manifest_and_parser() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    claimed_manifest_hash = manifest.pop("manifest_hash")
    assert canonical_hash(manifest) == claimed_manifest_hash

    compressed = BOOTSTRAP.read_bytes()
    assert len(compressed) == manifest["compressed_bytes"]
    assert hashlib.sha256(compressed).hexdigest() == manifest["compressed_sha256"]

    uncompressed = gzip.decompress(compressed)
    assert len(uncompressed) == manifest["uncompressed_bytes"]
    assert hashlib.sha256(uncompressed).hexdigest() == manifest["uncompressed_sha256"]

    state = parse_sector_radar_market_state(uncompressed.decode("utf-8"))
    assert state.state_hash == manifest["state_hash"]
    assert state.catalog_hash == manifest["catalog_hash"]
    assert state.formula_version == manifest["formula_version"]
    assert len(state.sessions) == manifest["session_count"] == 127
    assert state.sessions[0].isoformat() == manifest["session_start"]
    assert state.sessions[-1].isoformat() == manifest["session_end"] == "2026-09-04"
    assert len(state.series) == manifest["series_count"] == 321
    assert len(state.broad_identities) == manifest["broad_count"] == 90
    assert len(state.granular_identities) == manifest["granular_count"] == 230
    assert state.benchmark_thscode == "000300.SH"

    assert [item.workflow_run_id for item in state.source_lineage] == [
        33869436890,
        33878938737,
    ]
    assert [item.artifact_id for item in state.source_lineage] == [
        9936117543,
        9941301222,
    ]
    assert state.human_attention_authority == "NONE"
    assert state.investment_authority == "NONE"
    assert manifest["historical_membership_authority"] == "NONE"
    assert manifest["human_attention_authority"] == "NONE"
    assert manifest["investment_authority"] == "NONE"
