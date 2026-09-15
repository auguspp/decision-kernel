"""Exact new MU input preparation; no Web/Research/market execution in tests."""
from pathlib import Path
import hashlib

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime.external_research_execution import ExternalResearchInputPacket
from decision_kernel.runtime.external_research_identity import input_key

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "research_runs/candidates/MU.NASDAQ/p0-4a-MU-20260909T054933-55153397"


def test_mu_55153397_frozen_input_identity(capsys):
    raw = (CASE / "input.json").read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    assert blob == "bd4e215b025a8964c8349b8f7f64b576b23180ac"
    packet = ExternalResearchInputPacket.model_validate_json(raw)
    assert packet.execution_id == "p0-4a-MU-20260909T054933-55153397"
    assert packet.code_commit == "29f98409dddd0032259e05a4bdad7ebad60b8a76"
    assert packet.ticker == "MU" and packet.security_id == "NASDAQ:MU"
    assert packet.untrusted_test_material is None
    assert packet.budget.max_tool_calls == 60
    assert packet.budget.max_search_queries == 12
    assert packet.budget.max_source_reads == 48
    assert packet.budget.max_technical_retries == 0
    assert packet.budget.max_elapsed_minutes == 35
    assert input_key(packet).canonical_input_hash == canonical_hash(packet)
    with capsys.disabled():
        print("MU_55153397_INPUT_HASH=" + canonical_hash(packet), flush=True)
        print("MU_55153397_INPUT_BLOB=" + blob, flush=True)
        print("MU_55153397_PREPARATION_ONLY_NOT_RESEARCH_ACCEPTANCE", flush=True)
