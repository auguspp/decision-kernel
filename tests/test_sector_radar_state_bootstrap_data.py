from __future__ import annotations

import gzip
import hashlib
import json
import re
from pathlib import Path

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime.sector_radar_state import (
    parse_sector_radar_market_state,
)


BOOTSTRAP = Path("radar_inputs/sector-radar-state-bootstrap-2026-09-04.json.gz")
MANIFEST = Path(
    "radar_inputs/sector-radar-state-bootstrap-2026-09-04.manifest.json"
)
PROJECT_STATE = Path("docs/project-state.md")
HANDOFF = Path("docs/handoffs/2026-09-05-sector-radar-next-conversation.md")


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


def test_bootstrap_documentation_uses_manifest_as_canonical_identity() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    project_state = PROJECT_STATE.read_text(encoding="utf-8")
    handoff = HANDOFF.read_text(encoding="utf-8")
    manifest_path = MANIFEST.as_posix()

    rolling_state_section = project_state.split(
        "#### Rolling state and durable bootstrap\n",
        maxsplit=1,
    )[1].split(
        "\n#### HiThink sector-breadth acquisition",
        maxsplit=1,
    )[0]
    assert manifest_path in rolling_state_section
    assert "sole canonical source" in rolling_state_section
    stated_hashes = re.findall(
        r"^state hash = ([0-9a-f]{64})$",
        rolling_state_section,
        flags=re.MULTILINE,
    )
    assert stated_hashes == [manifest["state_hash"]]

    durable_data_section = handoff.split(
        "### Durable initial data\n",
        maxsplit=1,
    )[1].split(
        "\n### Main-branch health repair",
        maxsplit=1,
    )[0]
    assert manifest_path in durable_data_section
    assert "The manifest is authoritative" in durable_data_section
    assert manifest["state_hash"] not in durable_data_section
    assert not re.search(
        r"^state hash(?: =)? [0-9a-f]{64}$",
        durable_data_section,
        flags=re.MULTILINE,
    )
