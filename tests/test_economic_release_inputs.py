from __future__ import annotations

import copy
import html
import json
import shutil
from datetime import timedelta
from pathlib import Path
from urllib.error import URLError

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import economic_release_inputs as inputs
from decision_kernel.runtime import economic_release_discovery as discovery
from decision_kernel.runtime import economic_release_review as review
from decision_kernel.runtime import economic_market_context as view
from test_economic_release_review import (
    EXCERPTS, RECORDED, AS_OF, declaration, bytes_under,
)
from test_economic_release_discovery import (
    NOW, SOURCES, MOA, SPB, NEW_MOA, NEW_SPB, MOA_TITLE, SPB_TITLE,
    fixtures, response, listing, row,
)
from test_economic_market_context import links_for
from test_sector_radar_audit import prohibit_network, execute as produce, PRODUCED


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    prohibit_network(monkeypatch)
    monkeypatch.setattr(discovery, "fetch_discovery_page", lambda *a, **k: pytest.fail("no actual source requests"))


def setup(root):
    base = root / "inputs"
    base.mkdir(parents=True)
    seed = base / "seed.json"
    seed.write_text(json.dumps(SOURCES, ensure_ascii=False), encoding="utf-8")
    reviews = root / "reviews"
    reviews.mkdir()
    (reviews / ".gitkeep").write_bytes(b"")
    return seed, reviews


def ticks(start=AS_OF):
    values = iter(start + timedelta(seconds=i) for i in range(100))
    return lambda: next(values)


def pages():
    responses = fixtures()
    for url, excerpt in EXCERPTS.items():
        title = MOA_TITLE if url == NEW_MOA else SPB_TITLE
        body = ('<meta charset="utf-8">'
                f'<meta name="ArticleTitle" content="{title}"><meta name="PubDate" content="2026-09-04">'
                + ''.join(f'<p>{html.escape(line)}</p>' for line in excerpt.splitlines()))
        responses[url] = response(url, body)
    return responses


def accepted_case(root, monkeypatch, *, public=True):
    seed, reviews = setup(root)
    responses = pages()
    archive = root / "archive"
    if public:
        # Exercise the real public-labelled contract with ONLY synthetic HTML in
        # pytest tmp_path. Network remains blocked; no fixture is live evidence.
        monkeypatch.setattr(discovery, "fetch_discovery_page", responses.__getitem__)
        result = discovery.run_discovery(copy.deepcopy(SOURCES), archive, now=ticks(NOW))
        monkeypatch.setattr(discovery, "fetch_discovery_page", lambda *a, **k: pytest.fail("no source requests"))
    else:
        result = discovery.run_discovery(copy.deepcopy(SOURCES), archive,
            transport=responses.__getitem__, provenance=discovery.SYNTHETIC, now=ticks(NOW))
        source = [{**s, "capture_method": discovery.SYNTHETIC} for s in SOURCES]
        seed.write_text(json.dumps(source), encoding="utf-8")
    packet = result["review_packets"][0]
    form = declaration(archive, packet)
    item = review.apply_release_review(archive, form, reviews / "arbitrary-folder-name", now=lambda: RECORDED)
    return seed, reviews, archive, result, item


def test_empty_real_registry_preserves_seed_not_fabricated_acceptance(tmp_path):
    seed, reviews = setup(tmp_path)
    before = bytes_under(tmp_path)
    result = inputs.load_release_inputs(seed, reviews, as_of=AS_OF)
    assert result.receipt["accepted_bundle_count"] == 0
    assert result.receipt["known_url_count"] == 4
    assert len(result.seed_observations) == 4 and result.review_paths == ()
    assert {s["source_url"] for s in result.baseline} == {s["source_url"] for s in SOURCES}
    assert all(result.receipt[k] == "NONE" for k in inputs.AUTHORITY)
    assert not result.receipt["publisher_completeness"]
    assert not result.receipt["known_url_body_revisions_checked"]
    assert before == bytes_under(tmp_path)


def test_accepted_source_updates_known_urls_but_preserves_first_receipt(tmp_path, monkeypatch):
    seed, reviews, archive, result, accepted = accepted_case(tmp_path, monkeypatch)
    before = bytes_under(tmp_path)
    resolved = inputs.load_release_inputs(seed, reviews, as_of=AS_OF)
    assert resolved.receipt["known_url_count"] == 5
    assert resolved.receipt["accepted_bundle_count"] == 1
    assert resolved.receipt["review_receipts"][0]["acceptance_hash"] == accepted["acceptance_hash"]
    source = next(s for s in resolved.baseline if s["source_url"] == NEW_MOA)
    assert source == accepted["observation"]["source_record"]
    assert resolved.receipt["baseline_hash"] == canonical_hash(resolved.baseline)
    assert before == bytes_under(tmp_path)
    next_plan = discovery.discovery_plan(resolved.baseline, result["directories"])
    assert NEW_MOA not in next_plan["detail_requests"]
    assert NEW_SPB in next_plan["detail_requests"]
    assert any(e["source_url"] == NEW_MOA and e["discovery_disposition"] == "KNOWN_URL_NOT_REVALIDATED"
               for e in next_plan["entries"])


def test_directory_aliases_do_not_duplicate_reviews_or_periods(tmp_path, monkeypatch):
    seed, reviews, *_ = accepted_case(tmp_path, monkeypatch)
    a = inputs.load_release_inputs(seed, reviews, as_of=AS_OF)
    shutil.copytree(a.review_paths[0], reviews / "duplicate-alias")
    b = inputs.load_release_inputs(seed, reviews, as_of=AS_OF)
    assert a.receipt == b.receipt and a.baseline == b.baseline
    assert len(b.review_paths) == 1


@pytest.mark.parametrize("problem", ["missing", "loose-json", "draft", "nonempty-marker", "symlink"])
def test_invalid_registry_is_not_silently_empty(tmp_path, problem):
    seed, reviews = setup(tmp_path)
    if problem == "missing":
        shutil.rmtree(reviews)
    elif problem == "loose-json":
        (reviews / "observation.json").write_text("{}")
    elif problem == "draft":
        (reviews / "draft").mkdir()
        (reviews / "draft/review.json").write_text("{}")
    elif problem == "nonempty-marker":
        (reviews / ".gitkeep").write_text("not empty")
    else:
        (reviews / "alias").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises((ValueError, OSError)):
        inputs.load_release_inputs(seed, reviews, as_of=AS_OF)


@pytest.mark.parametrize("seed_error", ["missing-family", "duplicate-url", "future", "duplicate-key", "oversize"])
def test_invalid_seed_fails_before_scanning(tmp_path, seed_error):
    seed, reviews = setup(tmp_path)
    sources = copy.deepcopy(SOURCES)
    if seed_error == "missing-family":
        sources = sources[:2]
    elif seed_error == "duplicate-url":
        sources.append(sources[0])
    elif seed_error == "future":
        sources[0]["captured_at"] = (AS_OF + timedelta(days=1)).isoformat()
    seed.write_text(json.dumps(sources))
    if seed_error == "duplicate-key":
        seed.write_text('[{"source_kind":"MOA_LIVESTOCK_WEEKLY","source_kind":"SPB_EXPRESS_MONTHLY"}]')
    elif seed_error == "oversize":
        seed.write_bytes(b" " * (inputs.MAX_SEED_BYTES + 1))
    with pytest.raises(ValueError):
        inputs.run_release_input_scan(seed, reviews, tmp_path / "out", now=ticks())
    assert not (tmp_path / "out").exists()


def test_future_review_is_not_admitted_using_earlier_capture(tmp_path, monkeypatch):
    seed, reviews, *_ = accepted_case(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="cutoff"):
        inputs.load_release_inputs(seed, reviews, as_of=RECORDED - timedelta(microseconds=1))
    assert inputs.load_release_inputs(seed, reviews, as_of=RECORDED).receipt["accepted_bundle_count"] == 1


def test_synthetic_input_stays_synthetic_and_cannot_seed_public_scan(tmp_path, monkeypatch):
    seed, reviews, *_ = accepted_case(tmp_path, monkeypatch, public=False)
    loaded = inputs.load_release_inputs(seed, reviews, as_of=AS_OF)
    assert loaded.receipt["source_provenance"] == discovery.SYNTHETIC
    with pytest.raises(ValueError, match="public scanner"):
        inputs.run_release_input_scan(seed, reviews, tmp_path / "scan", now=ticks())
    seed.write_text(json.dumps(SOURCES))
    with pytest.raises(ValueError, match="mixed"):
        inputs.load_release_inputs(seed, reviews, as_of=AS_OF)


def test_budget_is_counted_before_loading_archives_no_truncation(tmp_path, monkeypatch):
    seed, reviews = setup(tmp_path)
    for n in range(inputs.MAX_RECORDS):
        (reviews / str(n)).mkdir()
    monkeypatch.setattr(inputs, "verify_release_review", lambda *a, **k: pytest.fail("must bound first"))
    with pytest.raises(ValueError, match="budget"):
        inputs.load_release_inputs(seed, reviews, as_of=AS_OF)


def test_rehashed_bad_acceptance_is_not_trusted(tmp_path, monkeypatch):
    seed, reviews, *_ = accepted_case(tmp_path, monkeypatch)
    path = reviews / "arbitrary-folder-name/acceptance.json"
    item = json.loads(path.read_text())
    item["observation"]["metrics"][0]["value"] = "999"
    item["acceptance_hash"] = canonical_hash({k: v for k, v in item.items() if k != "acceptance_hash"})
    path.write_bytes(review._data(item))
    with pytest.raises(ValueError):
        inputs.load_release_inputs(seed, reviews, as_of=AS_OF)


def test_baseline_identity_conflict_is_visible_and_does_not_scan(tmp_path, monkeypatch):
    seed, reviews, *_ = accepted_case(tmp_path, monkeypatch)
    # Valid source template, same URL but differing declared publication identity.
    changed = {**SOURCES[1], "source_url": NEW_MOA}
    seed.write_text(json.dumps([SOURCES[0], changed, *SOURCES[2:]]))
    loaded = inputs.load_release_inputs(seed, reviews, as_of=AS_OF)
    assert loaded.baseline == [] and loaded.receipt["baseline_conflicts"]
    report = inputs.run_release_input_scan(seed, reviews, tmp_path / "out", now=ticks())
    assert report["status"] == "BASELINE_IDENTITY_REVIEW_REQUIRED"
    assert not (tmp_path / "out/scan").exists()
    assert inputs.verify_release_input_scan(seed, reviews, tmp_path / "out") == report


def test_actual_scanner_receives_new_baseline_and_verifies_without_network(tmp_path, monkeypatch):
    seed, reviews, *_ = accepted_case(tmp_path, monkeypatch)
    responses = pages(); calls = []
    def transport(url):
        calls.append(url)
        return responses[url]
    before = bytes_under(reviews), seed.read_bytes()
    root = tmp_path / "run"
    report = inputs.run_release_input_scan(seed, reviews, root, now=ticks(), transport=transport)
    assert calls == [MOA, SPB, NEW_SPB]  # The accepted MOA URL is not refetched.
    assert report["status"] == inputs.READY
    assert report["scan_provenance"] == discovery.SYNTHETIC
    assert not report["known_url_body_revisions_checked"]
    assert inputs.verify_release_input_scan(seed, reviews, root) == report
    assert before == (bytes_under(reviews), seed.read_bytes())
    assert inputs.main(["verify", str(root), "--seed", str(seed), "--reviews-dir", str(reviews)]) == 0


def test_advanced_cutoff_cannot_hide_an_unreviewed_in_window_release(tmp_path, monkeypatch):
    seed, reviews, *_ = accepted_case(tmp_path, monkeypatch)
    responses = pages()
    intermediate = "https://xmsyj.moa.gov.cn/jcyj/202609/t20260902_8888881.htm"
    responses[MOA] = listing(MOA, [row(NEW_MOA, MOA_TITLE, "2026-09-04"),
        row(intermediate, "9月第1周畜产品和饲料集贸市场价格情况", "2026-09-02")])
    root = tmp_path / "run"
    result = inputs.run_release_input_scan(seed, reviews, root, now=ticks(), transport=responses.__getitem__)
    assert result["status"] == "UNREVIEWED_BASELINE_GAP"
    assert result["source_scan_status"] == "COMPLETE_BOUNDED_SCAN"
    assert result["unreviewed_baseline_gaps"][0]["source_url"] == intermediate
    assert inputs.main(["verify", str(root), "--seed", str(seed), "--reviews-dir", str(reviews)]) == 2
    assert "不是没有更新" in (root / "summary.md").read_text()


def test_partial_scan_is_not_promoted_by_valid_review_registry(tmp_path):
    seed, reviews = setup(tmp_path)
    responses = fixtures(new=False)
    def fetch(url):
        if url == MOA:
            raise URLError("fixture directory failure")
        return responses[url]
    root = tmp_path / "run"
    report = inputs.run_release_input_scan(seed, reviews, root, now=ticks(), transport=fetch)
    assert report["status"] == "INCOMPLETE_SCAN"
    assert inputs.verify_release_input_scan(seed, reviews, root) == report


@pytest.mark.parametrize("tamper", ["seed", "receipt", "summary", "extra"])
def test_scan_replay_requires_exact_inputs_and_reports(tmp_path, tamper):
    seed, reviews = setup(tmp_path)
    root = tmp_path / "run"
    inputs.run_release_input_scan(seed, reviews, root, now=ticks(), transport=fixtures(new=False).__getitem__)
    if tamper == "seed":
        seed.write_bytes(seed.read_bytes() + b"\n")
    elif tamper == "receipt":
        p = root / "input-set.json"; data = json.loads(p.read_text())
        data["accepted_bundle_count"] = 42
        data["input_set_hash"] = canonical_hash({k: v for k, v in data.items() if k != "input_set_hash"})
        p.write_bytes(review._data(data))
    elif tamper == "summary":
        (root / "summary.md").write_text("all verified, no updates")
    else:
        (root / "unexpected.json").write_text("{}")
    with pytest.raises(ValueError):
        inputs.verify_release_input_scan(seed, reviews, root)


def test_one_directory_context_uses_existing_cli_with_unchanged_candidate_state(tmp_path, monkeypatch):
    seed, reviews, *_ = accepted_case(tmp_path, monkeypatch, public=False)
    outcome, _, audit = produce(tmp_path / "market", jump=True)
    links = seed.parent / "links.json"
    links.write_text(canonical_json(links_for(outcome.persistent_bundle.market_state)))
    class Clock(inputs.datetime):
        @classmethod
        def now(cls, tz=None):
            return PRODUCED + timedelta(days=1)
    monkeypatch.setattr(view, "datetime", Clock)
    original = bytes_under(reviews), bytes_under(audit), seed.read_bytes()
    target = tmp_path / "reading"
    args = ["context", "--seed", str(seed), "--reviews-dir", str(reviews),
        "--bundle", str(audit / "expected/state"), "--parent-hints", str(audit / "inputs/parent-hints.json"),
        "--links", str(links), "--as-of", PRODUCED.isoformat(), "--output", str(target)]
    assert inputs.main(args) == 0
    assert (target / "index.html").is_file()
    p = json.loads((target / "association.json").read_text())["projection"]
    receipt = json.loads((target / "input-set.json").read_text())
    assert receipt["accepted_bundle_count"] == 1
    assert p["panels"][0]["economics"]["supplied_distinct_periods"] == 3
    assert p["new_events_created"] == 0
    assert p["source_review_receipts"][0]["acceptance_hash"] == receipt["review_receipts"][0]["acceptance_hash"]
    assert len(outcome.persistent_bundle.event_ledger.events) == 2
    assert original == (bytes_under(reviews), bytes_under(audit), seed.read_bytes())
    assert inputs.main(args) == 2  # No overwrite, even for repeated context generation.


def test_scan_output_is_new_and_outside_inputs(tmp_path):
    seed, reviews = setup(tmp_path)
    for output in (reviews / "nested", seed.parent / "nested", tmp_path, tmp_path / "decision-state/new"):
        with pytest.raises(ValueError):
            inputs.run_release_input_scan(seed, reviews, output, now=ticks())
