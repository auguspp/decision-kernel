from __future__ import annotations

import copy
import html
import json
from datetime import datetime, timedelta
from decimal import localcontext
from pathlib import Path
from urllib.error import URLError

import pytest
from bs4 import BeautifulSoup

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import economic_release_review as review
from decision_kernel.runtime import economic_market_context as view
from decision_kernel.runtime import economic_source_capture as capture
from decision_kernel.runtime.economic_node_study import qualify_release_excerpt
from test_economic_release_discovery import (
    NOW, SOURCES, MOA, SPB, NEW_MOA, NEW_SPB, MOA_TITLE, SPB_TITLE,
    execute as discover, fixtures, response, rehash,
)
from test_economic_market_context import links_for
from test_sector_radar_audit import resolution, execute as produce, PRODUCED, prohibit_network

REVIEWED = NOW + timedelta(minutes=5)
RECORDED = NOW + timedelta(minutes=10)
AS_OF = NOW + timedelta(days=1)
EXCERPTS = {
    NEW_MOA: MOA_TITLE + "\n日期：2026-09-04\n"
             "据对全国500个县集贸市场和采集点的监测，9月第1周（采集日为9月3日）\n"
             "全国生猪平均价格12.00元/公斤。\n全国玉米平均价格2.45元/公斤。\n"
             "育肥猪配合饲料平均价格3.34元/公斤。",
    NEW_SPB: SPB_TITLE + "\n日期：2026-09-04\n"
             "8月份，邮政行业业务收入完成1600亿元。其中，快递业务收入完成1400亿元。\n"
             "8月份，邮政行业寄递业务量完成200亿件。其中，快递业务量完成180亿件。",
}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    prohibit_network(monkeypatch)
    monkeypatch.setattr(capture, "fetch_public_page", lambda *a, **k: pytest.fail("no public fetch"))
    from decision_kernel.runtime import economic_release_discovery
    monkeypatch.setattr(economic_release_discovery, "fetch_discovery_page", lambda *a, **k: pytest.fail("no discovery fetch"))


def bytes_under(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def case(root, *, altered=None, partial=False, new=True):
    responses = fixtures(new=new)
    if new:
        for url, excerpt in EXCERPTS.items():
            text = altered if altered is not None and url == NEW_MOA else excerpt
            title = MOA_TITLE if url == NEW_MOA else SPB_TITLE
            body = ('<html><meta charset="utf-8">'
                    f'<meta name="ArticleTitle" content="{title}"><meta name="PubDate" content="2026-09-04">'
                    + ''.join(f'<p>{html.escape(line)}</p>' for line in text.splitlines()) + '</html>')
            responses[url] = response(url, body)
    if partial:
        responses[SPB] = URLError("synthetic unavailable directory")
    archive = root / "scan"
    result, calls = discover(archive, responses)
    return archive, result


def declaration(archive, packet, *, excerpt=None):
    draft, page = review.prepare_release_review(archive, packet["source_packet_id"])
    assert packet["title"] in page
    return {**draft, "decision": review.ACCEPT, "reviewer": "SYNTHETIC_REVIEWER",
            "reviewed_at": REVIEWED.isoformat(), "reason": "Fixture-only explicit excerpt review; not a Human decision.",
            "excerpt": EXCERPTS[packet["source_url"]] if excerpt is None else excerpt}


def accept(root, *, altered=None, partial=False):
    archive, result = case(root, altered=altered, partial=partial)
    packet = result["review_packets"][0]
    accepted = root / "accepted"
    form = declaration(archive, packet, excerpt=altered)
    item = review.apply_release_review(archive, form, accepted, now=lambda: RECORDED)
    return archive, result, form, accepted, item


def context(paths=(), *, observations=(), as_of=AS_OF, generated_at=AS_OF):
    r = resolution()
    return view.build_economic_market_context(market_state=r.market_state, event_ledger=r.event_ledger,
        observations=observations, links=links_for(r.market_state), as_of=as_of, generated_at=generated_at,
        reviewed_releases=paths)


def test_pending_draft_does_not_accept_any_observation(tmp_path):
    archive, result = case(tmp_path)
    original = bytes_under(archive)
    draft, _ = review.prepare_release_review(archive, result["review_packets"][0]["source_packet_id"])
    assert draft["decision"] == "PENDING_REVIEW" and draft["reviewed_at"] is None
    with pytest.raises(ValueError, match="explicit completed"):
        review.apply_release_review(archive, draft, tmp_path / "accepted", now=lambda: RECORDED)
    assert not (tmp_path / "accepted").exists()
    assert bytes_under(archive) == original
    assert result["observation_writes"] == 0


@pytest.mark.parametrize("index,node", [(0, "cn.livestock.price_feed"), (1, "cn.express.unit_economics")])
def test_exact_packet_acceptance_reuses_source_binder_and_keeps_all_clocks(tmp_path, index, node):
    archive, result = case(tmp_path)
    original = bytes_under(archive)
    packet = result["review_packets"][index]
    form = declaration(archive, packet)
    output = tmp_path / "accepted"
    item = review.apply_release_review(archive, form, output, now=lambda: RECORDED)
    assert item == review.verify_release_review(output, as_of=RECORDED)
    observation = item["observation"]
    assert observation["node_id"] == node
    assert observation["source_record"]["captured_at"] == packet["content_acquired_at"]
    assert datetime.fromisoformat(observation["system_pit_eligible_from"]) == datetime.fromisoformat(packet["content_acquired_at"])
    assert observation == qualify_release_excerpt(observation["source_record"])
    assert item["reviewed_at"] == REVIEWED.isoformat()
    assert item["eligible_from"] == item["recorded_at"]
    assert datetime.fromisoformat(item["recorded_at"]) == RECORDED
    assert item["provenance"] == observation["source_record"]["capture_method"] == review.SYNTHETIC
    assert item["reviewer_identity"] == "DECLARED_NOT_AUTHENTICATED"
    assert item["automatic_acceptance"] is False
    assert observation["historical_first_vintage_proven"] is False
    assert all(item[k] == "NONE" for k in review.AUTHORITY)
    assert bytes_under(output / "discovery") == original == bytes_under(archive)
    assert {p.name for p in output.iterdir()} == review.TOP_LEVEL
    assert not (output / "observation.json").exists(), "no loose export that loses review eligibility"
    assert item["binding"]["raw_body_sha256"] == packet["raw_body_sha256"]


@pytest.mark.parametrize("field", ["archive_hash", "source_packet_id", "raw_body_sha256"])
def test_wrong_archive_packet_or_body_is_not_an_acceptable_review(tmp_path, field):
    archive, result = case(tmp_path)
    form = declaration(archive, result["review_packets"][0]); form[field] = "0" * 64
    with pytest.raises(ValueError):
        review.apply_release_review(archive, form, tmp_path / "out", now=lambda: RECORDED)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("field,value", [
    ("decision", "REJECT"), ("decision", "DEFER"), ("decision", "PENDING_REVIEW"),
    ("reviewer", ""), ("reason", ""), ("reviewed_at", None),
    ("reviewed_at", "2026-09-05T12:05:00"), ("reviewed_at", NOW.isoformat()),
    ("reviewed_at", (RECORDED + timedelta(seconds=1)).isoformat()),
    ("schema_version", True), ("unexpected", "no guessed source metadata"),
])
def test_incomplete_or_temporally_invalid_review_cannot_be_published(tmp_path, field, value):
    archive, result = case(tmp_path)
    form = declaration(archive, result["review_packets"][0]); form[field] = value
    with pytest.raises(ValueError):
        review.apply_release_review(archive, form, tmp_path / "out", now=lambda: RECORDED)
    assert not (tmp_path / "out").exists()


def test_valid_looking_but_unsubstantiated_value_is_refused(tmp_path):
    archive, result = case(tmp_path)
    form = declaration(archive, result["review_packets"][0])
    form["excerpt"] = form["excerpt"].replace("12.00", "99.00")
    with pytest.raises(ValueError, match="fragment absent"):
        review.apply_release_review(archive, form, tmp_path / "out", now=lambda: RECORDED)
    assert not (tmp_path / "out").exists()


def test_unsupported_source_template_stays_pending_despite_explicit_accept(tmp_path):
    archive, result = case(tmp_path, altered=MOA_TITLE + "\n日期：2026-09-04\n新口径，未提供全国500县数据。")
    form = declaration(archive, result["review_packets"][0])
    form["excerpt"] = MOA_TITLE + "\n日期：2026-09-04\n新口径，未提供全国500县数据。"
    with pytest.raises(ValueError):
        review.apply_release_review(archive, form, tmp_path / "out", now=lambda: RECORDED)


def test_zero_packets_cannot_be_turned_into_a_real_acceptance(tmp_path):
    archive, result = case(tmp_path, new=False)
    assert result["review_packets"] == []
    with pytest.raises(ValueError, match="one exact"):
        review.prepare_release_review(archive, "0" * 64)


def test_scoped_acceptance_does_not_upgrade_an_incomplete_scan(tmp_path):
    archive, result, _, output, item = accept(tmp_path, partial=True)
    assert result["status"] == item["source_scan_status"] == "INCOMPLETE"
    assert review.verify_release_review(output)["source_scan_status"] == "INCOMPLETE"
    assert json.loads((archive / "result.json").read_text())["automatic_review_acceptance"] is False


def test_exact_reapply_is_idempotent_and_different_review_does_not_overwrite(tmp_path):
    archive, _, form, output, item = accept(tmp_path)
    original = bytes_under(output)
    def must_not_retime():
        pytest.fail("same acceptance must not acquire a later receipt time")
    assert review.apply_release_review(archive, form, output, now=must_not_retime) == item
    changed = {**form, "reason": "A separate review, not the old record."}
    with pytest.raises(ValueError, match="never overwrite"):
        review.apply_release_review(archive, changed, output)
    assert bytes_under(output) == original


@pytest.mark.parametrize("change", ["observation", "eligibility", "authority", "provenance"])
def test_rehashing_acceptance_does_not_bypass_original_reconstruction(tmp_path, change):
    _, _, _, output, _ = accept(tmp_path)
    path = output / "acceptance.json"
    payload = json.loads(path.read_text())
    if change == "observation":
        payload["observation"]["metrics"][0]["value"] = "99.00"
        payload["observation"]["observation_hash"] = canonical_hash({k: v for k, v in payload["observation"].items() if k != "observation_hash"})
    elif change == "eligibility":
        payload["eligible_from"] = NOW.isoformat()
    elif change == "authority":
        payload["investment_authority"] = "GRANTED"
    else:
        payload["provenance"] = review.LIVE
    payload["acceptance_hash"] = canonical_hash({k: v for k, v in payload.items() if k != "acceptance_hash"})
    path.write_bytes(review._data(payload))
    with pytest.raises(ValueError, match="reconstruct"):
        review.verify_release_review(output)


def test_rehashed_discovery_packet_is_recomputed_from_original_html(tmp_path):
    archive, result = case(tmp_path)
    result["review_packets"][0]["title"] = "伪造标题"
    rehash(archive, "result.json", review._data(result))
    with pytest.raises(ValueError, match="reconstruct"):
        review.prepare_release_review(archive, result["review_packets"][0]["source_packet_id"])


@pytest.mark.parametrize("stage", ["write", "rename"])
def test_interrupted_acceptance_does_not_publish_or_modify_inputs(tmp_path, monkeypatch, stage):
    archive, result = case(tmp_path)
    form = declaration(archive, result["review_packets"][0])
    original = bytes_under(archive)
    original_write, original_rename = Path.write_bytes, Path.rename
    def write(path, data):
        if path.name == "acceptance.json" and stage == "write":
            raise OSError("synthetic storage interruption")
        return original_write(path, data)
    def rename(path, target):
        if stage == "rename":
            raise OSError("synthetic publication interruption")
        return original_rename(path, target)
    monkeypatch.setattr(Path, "write_bytes", write)
    monkeypatch.setattr(Path, "rename", rename)
    with pytest.raises(OSError):
        review.apply_release_review(archive, form, tmp_path / "out", now=lambda: RECORDED)
    assert not (tmp_path / "out").exists()
    assert not list(tmp_path.glob(".economic-review-*"))
    assert bytes_under(archive) == original


def test_symlink_extra_file_and_oversized_review_are_rejected(tmp_path):
    archive, result, form, output, _ = accept(tmp_path)
    linked = tmp_path / "linked"; linked.symlink_to(output, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        review.verify_release_review(linked)
    (output / "extra.txt").write_text("not part of this receipt")
    with pytest.raises(ValueError, match="inventory"):
        review.verify_release_review(output)
    with pytest.raises(ValueError, match="outside"):
        review.apply_release_review(archive, form, archive / "nested", now=lambda: RECORDED)
    form["excerpt"] = "x" * review.MAX_REVIEW_BYTES
    with pytest.raises(ValueError, match="budget"):
        review.apply_release_review(archive, form, tmp_path / "oversized", now=lambda: RECORDED)


def test_new_review_connects_to_existing_panel_without_changing_market_or_ledger(tmp_path):
    _, _, _, output, item = accept(tmp_path)
    previous = qualify_release_excerpt({**SOURCES[1], "capture_method": review.SYNTHETIC})
    before = context(observations=[previous])
    after = context([output], observations=[previous])
    p = after["projection"]; economics = p["panels"][0]["economics"]
    assert economics["coverage"] == "TWO_PERIOD_DESCRIPTIVE_COMPARISON"
    assert economics["selected_periods"][-1]["end"] == "2026-09-03"
    assert economics["directions"]["live_hog_price"] == "UP"
    assert economics["fundamental_confirmation"] == "NOT_ESTABLISHED"
    assert p["market_state_hash"] == before["projection"]["market_state_hash"]
    assert p["event_ledger_hash"] == before["projection"]["event_ledger_hash"]
    assert p["panels"][0]["markets"][0]["saved_market"] == before["projection"]["panels"][0]["markets"][0]["saved_market"]
    assert p["new_events_created"] == 0
    assert datetime.fromisoformat(p["source_review_receipts"][0]["eligible_from"]) == RECORDED
    assert context([output, output], observations=[previous]) == after
    assert context([output], observations=[previous], generated_at=AS_OF + timedelta(days=1))["projection_hash"] == after["projection_hash"]
    page = view.render_economic_market_context(after)
    assert item["acceptance_hash"] in page and "不是 Human 投资判断" in page
    assert BeautifulSoup(page, "html.parser").find("script") is None


def test_capture_before_cutoff_cannot_smuggle_a_later_review_into_the_panel(tmp_path):
    _, _, _, output, item = accept(tmp_path)
    early = RECORDED - timedelta(microseconds=1)
    assert datetime.fromisoformat(item["observation"]["system_pit_eligible_from"]) < early
    with pytest.raises(ValueError, match="not recorded"):
        context([output], as_of=early)
    assert review.verify_release_review(output, as_of=RECORDED) == item
    with pytest.raises(ValueError, match="malformed economic"):
        context(observations=[item])  # bare acceptance is NOT an old pre-reviewed observation
    with pytest.raises(ValueError, match="mix synthetic"):
        context([output], observations=[qualify_release_excerpt(SOURCES[1])])


def test_newly_accepted_revision_stays_distinct_and_requires_version_review(tmp_path):
    _, _, _, first, _ = accept(tmp_path / "first")
    altered = EXCERPTS[NEW_MOA].replace("12.00", "12.20")
    _, _, _, second, _ = accept(tmp_path / "second", altered=altered)
    report = context([first, second])
    economics = report["projection"]["panels"][0]["economics"]
    assert economics["supplied_distinct_periods"] == 1
    assert economics["coverage"] == "VERSION_REVIEW_REQUIRED"
    assert economics["comparison"] is None
    assert len(economics["observations"]) == 2


def test_multiple_reviews_do_not_create_extra_economic_periods_and_html_is_escaped(tmp_path):
    archive, _, form, first, item = accept(tmp_path)
    form = {**form, "reviewer": '<script>alert("review")</script>'}
    second = tmp_path / "second"
    later = review.apply_release_review(archive, form, second, now=lambda: RECORDED + timedelta(minutes=1))
    assert item["observation"] == later["observation"]
    report = context([second, first]); p = report["projection"]
    assert len(p["source_review_receipts"]) == 2
    assert len(p["panels"][0]["economics"]["observations"]) == 1
    assert p["panels"][0]["economics"]["supplied_distinct_periods"] == 1
    assert context([first, second]) == report
    page = view.render_economic_market_context(report)
    assert '<script>' not in page and '&lt;script&gt;' in page


def test_decimal_context_does_not_change_accepted_source_or_panel(tmp_path):
    _, _, _, output, accepted = accept(tmp_path)
    expected = context([output])
    with localcontext() as numbers:
        numbers.prec = 6
        assert review.verify_release_review(output) == accepted
        assert context([output]) == expected


def test_full_cli_prepare_apply_verify_then_actual_bundle_association(tmp_path, monkeypatch):
    archive, result = case(tmp_path / "input")
    draft = tmp_path / "draft"
    packet = result["review_packets"][0]
    assert review.main(["prepare", str(archive), "--packet-id", packet["source_packet_id"], "--output", str(draft)]) == 0
    path = draft / "review.json"
    output = tmp_path / "accepted"
    assert review.main(["apply", str(archive), "--review", str(path), "--output", str(output)]) == 2
    path.write_bytes(review._data(declaration(archive, packet)))
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return RECORDED
    monkeypatch.setattr(review, "datetime", Clock)
    args = ["apply", str(archive), "--review", str(path), "--output", str(output)]
    assert review.main(args) == review.main(args) == 0
    assert review.main(["verify", str(output), "--as-of", RECORDED.isoformat()]) == 0
    class ViewClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return PRODUCED + timedelta(days=1)
    monkeypatch.setattr(view, "datetime", ViewClock)
    outcome, _, audit = produce(tmp_path / "market", jump=True)
    bundle = outcome.persistent_bundle
    inputs = tmp_path / "links"; inputs.mkdir()
    links = inputs / "links.json"; links.write_text(canonical_json(links_for(bundle.market_state)))
    original = bytes_under(output), bytes_under(audit)
    target = tmp_path / "reading"
    cli = ["--bundle", str(audit / "expected/state"), "--parent-hints", str(audit / "inputs/parent-hints.json"),
           "--links", str(links), "--reviewed-release", str(output), "--as-of", PRODUCED.isoformat(), "--output", str(target)]
    assert view.main(cli) == 0
    report = json.loads((target / "association.json").read_text())
    assert report["projection"]["new_events_created"] == 0
    assert datetime.fromisoformat(report["projection"]["source_review_receipts"][0]["eligible_from"]) == RECORDED
    assert len(bundle.event_ledger.events) == 2
    assert original == (bytes_under(output), bytes_under(audit))
    assert view.main(cli) == 2, "do not overwrite existing reports"
    path.write_text('{"schema_version":1,"schema_version":1}')
    assert review.main(["apply", str(archive), "--review", str(path), "--output", str(tmp_path / "bad")]) == 2
