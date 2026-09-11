from __future__ import annotations

import json
from pathlib import Path

from decision_kernel.xiaohongshu_harness import (
    build_writing_brief,
    load_authoring_spec,
    load_deep_research_package,
    load_style_sample_bank,
    render_planner_prompt,
)


ROOT = Path(__file__).resolve().parents[1]
SANHUA_RESEARCH = ROOT / "research_cases" / "002050-sanhua-deep-research-v1.json"
SANHUA_AUTHORING = ROOT / "eval" / "xiaohongshu" / "002050-sanhua-authoring-v1.json"
REGRESSION = ROOT / "eval" / "xiaohongshu" / "hengrui-price-led-regression-v1.json"
HENGRUI_RECORD = (
    ROOT
    / "docs"
    / "dogfood"
    / "xiaohongshu-hengrui-human-accepted-draft-2026-09-11.md"
)


def _fixture() -> dict:
    return json.loads(REGRESSION.read_text(encoding="utf-8"))


def _brief():
    return build_writing_brief(
        load_deep_research_package(SANHUA_RESEARCH),
        load_authoring_spec(SANHUA_AUTHORING),
    )


def _hengrui_sample():
    bank = load_style_sample_bank()
    return next(sample for sample in bank.samples if sample.sample_id == "hengrui-price-expectation-gap")


def test_hengrui_reference_remains_human_reference_not_high_read() -> None:
    fixture = _fixture()
    sample = _hengrui_sample()

    assert fixture["status"] == "HUMAN_ACCEPTED_DRAFT_NOT_HIGH_READ"
    assert sample.performance_label == "HUMAN_REFERENCE"
    assert sample.title_pattern == fixture["accepted_title"]


def test_hengrui_price_led_lessons_are_injected_into_planner_prompt() -> None:
    fixture = _fixture()
    sample = _hengrui_sample()
    prompt = render_planner_prompt(_brief())

    lesson_text = "\n".join(sample.reusable_lessons)
    for marker in fixture["must_survive_in_planner_prompt"]:
        assert marker in lesson_text
        assert marker in prompt


def test_hengrui_failure_modes_remain_regression_calibration() -> None:
    fixture = _fixture()
    sample = _hengrui_sample()
    failure_text = "\n".join(sample.failure_modes)

    for marker in fixture["must_survive_failure_modes"]:
        assert marker in failure_text


def test_hengrui_rejected_examples_are_preserved_as_negative_examples() -> None:
    fixture = _fixture()
    record = HENGRUI_RECORD.read_text(encoding="utf-8")

    assert "HUMAN_ACCEPTED_DRAFT / STRUCTURE+VOICE CALIBRATION" in record
    for example in fixture["rejected_examples"]:
        assert example in record


def test_price_led_regression_spine_keeps_required_return_in_second_layer() -> None:
    fixture = _fixture()

    assert fixture["required_spine"] == [
        "current_price",
        "implied_expectations",
        "observed_reality",
        "expectation_gap",
        "gap_closing_paths",
        "evidence_for_each_path",
        "required_return_as_second_layer",
        "extra_conditions_for_required_return",
        "return_to_current_price",
    ]
