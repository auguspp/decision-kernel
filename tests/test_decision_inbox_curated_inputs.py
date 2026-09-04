import json
from pathlib import Path


WORKFLOW_PATH = Path(".github/workflows/decision-inbox.yml")


def _between(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


def _argument_lines(step: str) -> tuple[str, ...]:
    return tuple(
        line.strip()
        for line in step.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def _bash_array_entries(step: str, name: str) -> tuple[str, ...]:
    body = step.split(f"{name}=(", 1)[1].split(")", 1)[0]
    return tuple(
        line.strip()
        for line in body.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def test_scheduled_human_inbox_uses_attention_composition_and_curated_inputs() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    inbox_step = _between(
        workflow,
        "- name: Build Attention Inbox",
        "- name: Capture Surprise Radar market-history shadow",
    )

    assert "python -m decision_kernel.runtime.attention_inbox" in inbox_step
    assert "decision-kernel build-inbox" not in inbox_step

    expected_current_inputs = {
        "dogfood/600519-moutai.json",
        "dogfood/300750-catl.json",
        "dogfood/601088-shenhua.json",
        "research_cases/603986-gigadevice-deep-research-v2.json",
        "research_cases/002050-sanhua-deep-research-v1.json",
    }
    decision_inputs = set(_bash_array_entries(inbox_step, "decision_packages"))

    assert decision_inputs == expected_current_inputs
    assert "dogfood/600036-cmb.json" not in decision_inputs
    assert not any("*" in path for path in decision_inputs)


def test_scheduled_research_attention_is_explicit_and_has_no_stale_current_handoff() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    inbox_step = _between(
        workflow,
        "- name: Build Attention Inbox",
        "- name: Capture Surprise Radar market-history shadow",
    )
    research_inputs = _bash_array_entries(inbox_step, "research_attention_handoffs")

    # No unresolved DEEPEN_REQUIRED handoff exists in current state. In particular,
    # the frozen Tinavi cold-start handoff has already resolved into Full Research
    # plus a Human WATCH decision and must not recur as a stale daily card.
    assert research_inputs == ()
    assert 'research_attention_args+=(--research-attention "$handoff")' in inbox_step
    assert '"${research_attention_args[@]}"' in inbox_step


def test_shadow_sampling_uses_exact_research_package_objects() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    shadow_step = _between(
        workflow,
        "- name: Capture Surprise Radar market-history shadow",
        "- name: Publish Human summary",
    )
    shadow_inputs = set(_bash_array_entries(shadow_step, "shadow_packages"))

    expected_shadow_inputs = {
        "dogfood/600519-moutai.json",
        "dogfood/300750-catl.json",
        "dogfood/600036-cmb.json",
        "dogfood/601088-shenhua.json",
        "research_cases/603986-gigadevice-deep-research-v2.json",
        "research_cases/002050-sanhua-deep-research-v1.json",
    }

    assert shadow_inputs == expected_shadow_inputs
    assert '"${shadow_packages[@]}"' in shadow_step
    assert "dogfood/*.json" not in _argument_lines(shadow_step)
    assert not any("688277-tinavi" in path for path in shadow_inputs)

    # File presence in a heterogeneous dogfood directory must not qualify an
    # Evidence array or Research-attention handoff as a market-history package.
    for path in shadow_inputs:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        assert isinstance(payload, dict), path


def test_legacy_cmb_fixture_can_remain_non_authoritative_outside_human_inbox() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    inbox_step = _between(
        workflow,
        "- name: Build Attention Inbox",
        "- name: Capture Surprise Radar market-history shadow",
    )
    shadow_step = _between(
        workflow,
        "- name: Capture Surprise Radar market-history shadow",
        "- name: Publish Human summary",
    )
    disclosure_step = _between(
        workflow,
        "- name: Scan official disclosures and prepare Research handoffs",
        "- name: Publish disclosure summary",
    )

    assert "dogfood/600036-cmb.json" not in _bash_array_entries(
        inbox_step, "decision_packages"
    )
    assert "dogfood/600036-cmb.json" in _bash_array_entries(
        shadow_step, "shadow_packages"
    )
    assert any(
        line.startswith("dogfood/600036-cmb.json")
        for line in _argument_lines(disclosure_step)
    )
