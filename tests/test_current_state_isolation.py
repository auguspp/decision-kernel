"""Malformed saved shapes do not couple independently validated read inputs."""
from decision_kernel.runtime import current_state as read
from decision_kernel.runtime import current_state_delivery as delivery
from test_current_state import AT, SHA, run
from test_current_state_delivery import API


def test_malformed_saved_input_isolated_in_its_lane(monkeypatch, tmp_path):
    collector = delivery.Collector(API(), SHA, tmp_path, now=lambda: AT)
    monkeypatch.setattr(collector, "runs", lambda lane: ([run()], True))
    def malformed(lane, chosen):
        raise TypeError("malformed saved JSON shape")
    monkeypatch.setattr(collector, "saved_product", malformed)
    result = collector.lane("sector")
    assert result["health"] == "LATEST_SUCCESS_INPUT_REJECTED"
    assert result["last_qualified_result"] is None
    assert "TypeError" in result["gaps"][0]


def test_invalid_live_package_does_not_block_registered_valid_quick(monkeypatch, tmp_path):
    from test_current_state import handoff
    values = {
        read.WORKFLOWS["inbox"]: b"decision_packages=(\n bad.json\n)\nresearch_attention_handoffs=(\n quick.json\n)\n",
        "bad.json": b"null", "quick.json": handoff(),
    }
    collector = delivery.Collector(API(), SHA, tmp_path, now=lambda: AT)
    def source(spec):
        return values[spec["path"]], {"path": spec["path"], "ref": SHA}
    monkeypatch.setattr(collector, "source", source)
    result = collector.research({"references": [], "historical_handoffs": []})
    assert result["gaps"][0]["status"] == "PRODUCTION_INPUT_REJECTED_NOT_REMOVED"
    assert len(result["handoffs"]["active"]) == 1
    assert not result["handoffs"]["gaps"]
