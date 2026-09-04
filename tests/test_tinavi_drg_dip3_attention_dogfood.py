import json
from datetime import datetime, timezone
from pathlib import Path

from decision_kernel.evidence import EvidenceArtifact
from decision_kernel.research_workflow_v1 import (
    ResearchFunnelTerminalState,
    run_research_funnel,
)
from decision_kernel.runtime.attention_inbox import (
    parse_research_attention_handoff,
    render_attention_inbox_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "dogfood/688277-tinavi-drg-dip3-evidence-2026-09-04.json"
HANDOFF_PATH = ROOT / "dogfood/688277-tinavi-drg-dip3-research-attention-2026-09-04.json"


def test_tinavi_drg_dip3_real_discovery_replays_through_existing_funnel() -> None:
    evidence = tuple(
        EvidenceArtifact.model_validate(item)
        for item in json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    )
    handoff = parse_research_attention_handoff(
        HANDOFF_PATH.read_text(encoding="utf-8")
    )
    frozen = handoff.research_funnel

    replayed = run_research_funnel(
        discovery=frozen.discovery,
        pre_research=frozen.pre_research,
        quick_research=frozen.quick_research,
        evidence_artifacts=evidence,
    )

    assert replayed == frozen
    assert replayed.terminal_state is ResearchFunnelTerminalState.DEEPEN_REQUIRED
    assert replayed.investment_authority == "NONE"

    surface = render_attention_inbox_markdown(
        (),
        (handoff,),
        generated_at=datetime(2026, 9, 4, 1, 21, tzinfo=timezone.utc),
    )
    assert "## 天智航 688277" in surface
    assert "DEEPEN_REQUIRED" in surface
    assert "尚未建立 frozen Research · Odds 未生成" in surface
    assert "INDUSTRY_DISCOVERY" in surface
    assert "Investment Authority = NONE" in surface
