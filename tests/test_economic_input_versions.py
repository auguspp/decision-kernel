from __future__ import annotations

import json
import shutil
from datetime import timedelta
from decimal import localcontext

import pytest

from decision_kernel.identity import canonical_json
from decision_kernel.runtime import economic_release_inputs as inputs
from decision_kernel.runtime import economic_market_context as view
from test_economic_release_inputs import accepted_case, setup, no_network
from test_economic_release_review import EXCERPTS, AS_OF, bytes_under
from test_economic_release_discovery import NEW_MOA
from test_economic_market_context import links_for
from test_sector_radar_audit import resolution, execute as produce, PRODUCED


def test_same_url_body_revision_remains_two_economic_versions(tmp_path, monkeypatch):
    seed, reviews, *_ = accepted_case(tmp_path / "first", monkeypatch)
    monkeypatch.setitem(EXCERPTS, NEW_MOA, EXCERPTS[NEW_MOA].replace("12.00", "13.00"))
    _, revised, *_ = accepted_case(tmp_path / "second", monkeypatch)
    shutil.copytree(revised / "arbitrary-folder-name", reviews / "second-version")
    loaded = inputs.load_release_inputs(seed, reviews, as_of=AS_OF)
    assert loaded.receipt["known_url_count"] == 5
    assert loaded.receipt["accepted_bundle_count"] == 2
    assert loaded.receipt["baseline_status"] == "READY"  # Only URL/title/date identity.
    state = resolution()
    report = view.build_economic_market_context(market_state=state.market_state,
        event_ledger=state.event_ledger, observations=loaded.seed_observations,
        reviewed_releases=loaded.review_paths, links=links_for(state.market_state),
        as_of=AS_OF, generated_at=AS_OF)
    economics = report["projection"]["panels"][0]["economics"]
    assert economics["coverage"] == "VERSION_REVIEW_REQUIRED"
    assert economics["comparison"] is None
    assert len(report["projection"]["source_review_receipts"]) == 2
    assert report["projection"]["new_events_created"] == 0


def test_receipt_identity_is_independent_of_caller_decimal_precision(tmp_path, monkeypatch):
    seed, reviews, *_ = accepted_case(tmp_path, monkeypatch)
    expected = inputs.load_release_inputs(seed, reviews, as_of=AS_OF)
    with localcontext() as ctx:
        ctx.prec = 4
        actual = inputs.load_release_inputs(seed, reviews, as_of=AS_OF)
    assert expected.receipt == actual.receipt
    assert expected.baseline == actual.baseline


def test_context_sidecar_write_failure_removes_only_new_report(tmp_path, monkeypatch):
    seed, reviews = setup(tmp_path)
    outcome, _, audit = produce(tmp_path / "market", jump=True)
    links = seed.parent / "links.json"
    links.write_text(canonical_json(links_for(outcome.persistent_bundle.market_state)))
    class Clock(inputs.datetime):
        @classmethod
        def now(cls, tz=None):
            return PRODUCED + timedelta(days=1)
    monkeypatch.setattr(view, "datetime", Clock)
    target = tmp_path / "context"
    old = bytes_under(audit), bytes_under(reviews), seed.read_bytes()
    original = inputs.Path.write_bytes
    def fail(path, data):
        if path == target / "input-set.json":
            raise OSError("synthetic sidecar failure")
        return original(path, data)
    monkeypatch.setattr(inputs.Path, "write_bytes", fail)
    with pytest.raises(OSError, match="sidecar"):
        inputs.render_input_context(seed, reviews, as_of=PRODUCED, output=target,
            bundle=audit / "expected/state", parent_hints=audit / "inputs/parent-hints.json", links=links)
    assert not target.exists()
    assert old == (bytes_under(audit), bytes_under(reviews), seed.read_bytes())
