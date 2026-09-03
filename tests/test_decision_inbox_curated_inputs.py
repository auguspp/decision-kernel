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


def test_scheduled_human_inbox_uses_explicit_curated_inputs() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    inbox_step = _between(
        workflow,
        "- name: Build Decision Inbox",
        "- name: Capture Surprise Radar market-history shadow",
    )
    argument_lines = _argument_lines(inbox_step)

    assert not any(line.startswith("dogfood/*.json") for line in argument_lines)
    assert not any(line.startswith("dogfood/600036-cmb.json") for line in argument_lines)

    expected_current_inputs = {
        "dogfood/600519-moutai.json",
        "dogfood/300750-catl.json",
        "dogfood/601088-shenhua.json",
        "research_cases/603986-gigadevice-deep-research-v2.json",
        "research_cases/002050-sanhua-deep-research-v1.json",
    }
    for path in expected_current_inputs:
        assert any(line.startswith(path) for line in argument_lines)


def test_legacy_cmb_fixture_can_remain_non_authoritative_outside_human_inbox() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    inbox_step = _between(
        workflow,
        "- name: Build Decision Inbox",
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

    assert not any(
        line.startswith("dogfood/600036-cmb.json")
        for line in _argument_lines(inbox_step)
    )
    assert any(
        line.startswith("dogfood/*.json") for line in _argument_lines(shadow_step)
    )
    assert any(
        line.startswith("dogfood/600036-cmb.json")
        for line in _argument_lines(disclosure_step)
    )
