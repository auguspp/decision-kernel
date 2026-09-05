from __future__ import annotations

import copy
import html
import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.runtime import economic_release_discovery as discovery


SOURCES = json.loads(Path("radar_inputs/economic-node-study-2026-09-05.json").read_text(encoding="utf-8"))
NOW = datetime(2026, 9, 5, 12, tzinfo=timezone.utc)
MOA = discovery.DIRECTORIES["MOA_FEED"]
SPB = discovery.DIRECTORIES["SPB_EXPRESS"]
NEW_MOA = "https://xmsyj.moa.gov.cn/jcyj/202609/t20260904_9999999.htm"
NEW_SPB = "https://www.spb.gov.cn/gjyzj/c100015/c100016/202609/" + "a" * 32 + ".shtml"
MOA_TITLE = "9月第1周畜产品和饲料集贸市场价格情况"
SPB_TITLE = "国家邮政局公布2026年1-8月邮政行业运行情况"
NEWS_URL = "https://www.spb.gov.cn/gjyzj/c100015/c100016/202609/" + "c" * 32 + ".shtml"


def response(url, text):
    body = text.encode("utf-8")
    return discovery.PublicResponse(url, 200, {"content-type": "text/html; charset=utf-8", "content-length": str(len(body))}, body)


def row(url, title, day):
    return f'<li><a href="{html.escape(url, quote=True)}" title="{html.escape(title, quote=True)}">{html.escape(title)}</a><span>{day}</span></li>'


def listing(url, rows):
    return response(url, '<html><meta charset="utf-8"><body><ul>' + "".join(rows) + '</ul></body></html>')


def detail(url, title, day="2026-09-04"):
    return response(url, f'<html><meta charset="utf-8"><meta name="ArticleTitle" content="{title}"><meta name="PubDate" content="{day} 10:00:00"><h1>{title}</h1><p>Unreviewed synthetic facts only.</p></html>')


def fixtures(*, new=True):
    moa = [row(SOURCES[1]["source_url"], SOURCES[1]["title"], SOURCES[1]["published_date"]),
           row("https://xmsyj.moa.gov.cn/jcyj/202608/t20260819_8888888.htm", "8月第2周畜产品和饲料集贸市场价格情况", "2026-08-19")]
    spb = [row(NEWS_URL, "普通行业新闻不是月度经济发布", "2026-09-04")]
    result = {}
    if new:
        moa.insert(0, row(NEW_MOA, MOA_TITLE, "2026-09-04"))
        spb.insert(0, row(NEW_SPB, SPB_TITLE, "2026-09-04"))
        result.update({NEW_MOA: detail(NEW_MOA, MOA_TITLE), NEW_SPB: detail(NEW_SPB, SPB_TITLE)})
    result.update({MOA: listing(MOA, moa), SPB: listing(SPB, spb)})
    return result


def execute(root, responses=None):
    responses = fixtures() if responses is None else responses
    calls = []
    ticks = iter(NOW + timedelta(seconds=i) for i in range(100))

    def fetch(url):
        calls.append(url)
        item = responses[url]
        if isinstance(item, Exception):
            raise item
        return item

    baseline = copy.deepcopy(SOURCES)
    result = discovery.run_discovery(baseline, root, transport=fetch, provenance=discovery.SYNTHETIC, now=lambda: next(ticks))
    assert baseline == SOURCES
    return result, calls


def rehash(root, name, data):
    (root / name).write_bytes(data)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"][name] = {"bytes": len(data), "sha256": discovery._sha(data)}
    manifest.pop("archive_hash")
    manifest["archive_hash"] = canonical_hash(manifest)
    (root / "manifest.json").write_bytes(discovery._bytes(manifest))


def test_complete_scan_reconstructs_pending_review_without_accepting_facts(tmp_path, monkeypatch):
    root = tmp_path / "scan"
    result, calls = execute(root)
    assert calls == [MOA, SPB, NEW_MOA, NEW_SPB]
    assert result["status"] == "COMPLETE_BOUNDED_SCAN"
    assert result["provenance"] == discovery.SYNTHETIC
    assert result["complete_publisher_coverage"] is False
    assert result["observation_writes"] == result["market_event_writes"] == 0
    assert result["automatic_review_acceptance"] is False
    assert result["known_url_body_revisions_checked"] is False
    assert len(result["review_packets"]) == 2
    for packet in result["review_packets"]:
        assert packet["status"] == "PENDING_HUMAN_SOURCE_REVIEW"
        assert not packet["metrics_extracted"] and not packet["economic_observation_written"]
        assert not packet["historical_first_vintage_proven"]
        assert packet["human_attention_authority"] == packet["research_authority"] == packet["investment_authority"] == "NONE"
        assert datetime.fromisoformat(packet["content_acquired_at"]) > datetime.fromisoformat(packet["directory_observed_at"])
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    monkeypatch.setattr(discovery, "fetch_discovery_page", lambda url: pytest.fail("verification must not fetch"))
    assert discovery.verify_discovery(root)["review_packet_count"] == 2
    assert discovery.main(["verify", str(root)]) == 0
    assert before == {p.name: p.read_bytes() for p in root.iterdir()}


def test_known_and_older_records_are_not_refetched_or_called_new_releases(tmp_path):
    result, calls = execute(tmp_path / "scan", fixtures(new=False))
    assert calls == [MOA, SPB]
    assert result["review_packets"] == []
    assert result["directories"][1]["rows"][0]["target_family"] is False
    dispositions = {entry["discovery_disposition"] for entry in result["plan"]["entries"]}
    assert dispositions == {"KNOWN_URL_NOT_REVALIDATED", "OLDER_UNREVIEWED_BACKLOG_NOT_FETCHED"}
    assert "not proof of no publisher update" in (tmp_path / "scan" / "summary.md").read_text(encoding="utf-8")


def test_relative_anchor_and_repeated_identical_url_are_deduplicated():
    r = row("./202609/t20260904_9999999.htm", MOA_TITLE, "2026-09-04")
    parsed = discovery.parse_directory("MOA_FEED", listing(MOA, [r, r]), captured_at=NOW)
    assert len(parsed["rows"]) == 1
    assert parsed["rows"][0]["source_url"] == NEW_MOA
    assert parsed["rows"][0]["anchor_line"] >= 1


@pytest.mark.parametrize("href", ["https://evil.invalid/page", "http://xmsyj.moa.gov.cn/jcyj/202609/t20260904_9999999.htm", "javascript:alert(1)", NEW_MOA + "?token=secret", NEW_MOA + "#fragment", "https://xmsyj.moa.gov.cn@127.0.0.1/", "//evil.invalid/page"])
def test_target_titles_cannot_authorize_unreviewed_urls(href):
    with pytest.raises(discovery.ReleaseDiscoveryError, match="allowed article family"):
        discovery.parse_directory("MOA_FEED", listing(MOA, [row(href, MOA_TITLE, "2026-09-04")]), captured_at=NOW)


@pytest.mark.parametrize("day", ["", "09-04", "2026-09-04 2026-09-03", "2026-02-30", "2026-09-06"])
def test_missing_ambiguous_invalid_or_future_listing_dates_fail(day):
    with pytest.raises(ValueError):
        discovery.parse_directory("MOA_FEED", listing(MOA, [row(NEW_MOA, MOA_TITLE, day)]), captured_at=NOW)


def test_same_url_conflicting_metadata_is_not_silently_deduplicated():
    with pytest.raises(discovery.ReleaseDiscoveryError, match="conflicting"):
        discovery.parse_directory("MOA_FEED", listing(MOA, [row(NEW_MOA, MOA_TITLE, "2026-09-04"), row(NEW_MOA, MOA_TITLE, "2026-09-03")]), captured_at=NOW)


def test_known_url_changed_title_requires_review_even_if_outside_old_title_pattern(tmp_path):
    responses = fixtures(new=False)
    source = SOURCES[1]
    responses[MOA] = listing(MOA, [row(source["source_url"], "更正公告：原发布口径有变", source["published_date"])])
    responses[source["source_url"]] = detail(source["source_url"], "更正公告：原发布口径有变", source["published_date"])
    result, calls = execute(tmp_path / "scan", responses)
    assert calls[-1] == source["source_url"]
    assert result["plan"]["entries"][0]["discovery_disposition"] == "KNOWN_METADATA_CHANGED_REVIEW_REQUIRED"
    assert result["review_packets"][0]["status"] == "PENDING_HUMAN_SOURCE_REVIEW"


def test_budget_excess_keeps_all_candidates_and_fetches_no_top_n(tmp_path):
    responses = fixtures(new=False)
    rows = [row(f"https://xmsyj.moa.gov.cn/jcyj/202609/t20260904_{9000000+i}.htm", MOA_TITLE, "2026-09-04") for i in range(5)]
    responses[MOA] = listing(MOA, rows)
    root = tmp_path / "scan"
    result, calls = execute(root, responses)
    assert calls == [MOA, SPB]
    assert result["status"] == "INCOMPLETE"
    assert result["plan"]["candidate_count"] == 5
    assert len(result["plan"]["detail_candidates"]) == 5
    assert result["plan"]["detail_requests"] == []
    assert discovery.verify_discovery(root)["status"] == "INCOMPLETE"
    assert discovery.main(["verify", str(root)]) == 2


def test_unavailable_directory_is_not_a_no_new_release_result(tmp_path):
    responses = fixtures(new=False)
    responses[MOA] = URLError("private untrusted exception text")
    root = tmp_path / "scan"
    result, calls = execute(root, responses)
    assert calls == [MOA, SPB]
    assert result["status"] == "INCOMPLETE"
    assert result["directories"][0]["coverage"] == "UNKNOWN_NOT_A_NO_NEW_RELEASE_RESULT"
    assert all(b"private untrusted" not in p.read_bytes() for p in root.iterdir())
    assert discovery.verify_discovery(root)["status"] == "INCOMPLETE"


def test_blank_or_script_only_directory_is_not_quiet(tmp_path):
    responses = fixtures(new=False)
    responses[MOA] = response(MOA, '<script>' + row(NEW_MOA, MOA_TITLE, "2026-09-04") + '</script>')
    result, calls = execute(tmp_path / "scan", responses)
    assert result["status"] == "INCOMPLETE"
    assert calls == [MOA, SPB]


@pytest.mark.parametrize("alteration", ["title", "date", "url", "duplicate_meta"])
def test_detail_identity_mismatch_never_yields_accepted_observation(tmp_path, alteration):
    responses = fixtures()
    if alteration == "title":
        responses[NEW_MOA] = detail(NEW_MOA, "changed title")
    elif alteration == "date":
        responses[NEW_MOA] = detail(NEW_MOA, MOA_TITLE, "2026-09-03")
    elif alteration == "url":
        responses[NEW_MOA] = detail(NEW_SPB, MOA_TITLE)
    else:
        body = responses[NEW_MOA].body.decode("utf-8") + '<meta name="PubDate" content="2026-09-04">'
        responses[NEW_MOA] = response(NEW_MOA, body)
    root = tmp_path / "scan"
    result, calls = execute(root, responses)
    assert result["status"] == "INCOMPLETE"
    assert result["review_packets"][0]["status"] == "SOURCE_IDENTITY_OR_TRANSPORT_REVIEW_REQUIRED"
    assert (root / "02.body.bin").is_file()
    assert discovery.verify_discovery(root)["status"] == "INCOMPLETE"


def test_http_error_is_recorded_once_closed_without_reading_unsafe_body(tmp_path):
    class Body(io.BytesIO):
        def read(self, *args):
            pytest.fail("must not read HTTP error body")
    body = Body(b"private error body")
    responses = fixtures(new=False)
    responses[MOA] = HTTPError("https://invalid/?token=private", 403, "private reason", {}, body)
    root = tmp_path / "scan"
    result, calls = execute(root, responses)
    assert body.closed and calls == [MOA, SPB]
    record = json.loads((root / "00.request.json").read_text(encoding="utf-8"))
    assert record["http_status"] == 403
    assert record["body_retained"] is False
    assert all(b"private" not in p.read_bytes() for p in root.iterdir())
    assert discovery.verify_discovery(root)["status"] == "INCOMPLETE"


@pytest.mark.parametrize("target", ["result", "summary", "request_order", "status"])
def test_rehashing_outer_inventory_cannot_hide_inconsistent_outputs(tmp_path, target):
    root = tmp_path / "scan"
    execute(root)
    if target == "result":
        data = json.loads((root / "result.json").read_text(encoding="utf-8"))
        data["review_packets"][0]["status"] = "APPROVED"
        rehash(root, "result.json", discovery._bytes(data))
    elif target == "summary":
        rehash(root, "summary.md", b"everything is approved\n")
    else:
        data = json.loads((root / "02.request.json").read_text(encoding="utf-8"))
        data["url" if target == "request_order" else "http_status"] = NEW_SPB if target == "request_order" else 403
        rehash(root, "02.request.json", discovery._bytes(data))
    with pytest.raises(discovery.ReleaseDiscoveryError):
        discovery.verify_discovery(root)


def test_same_sources_in_two_scan_archives_keep_packet_identity_but_not_fake_history(tmp_path):
    first, _ = execute(tmp_path / "first")
    second, _ = execute(tmp_path / "second")
    assert first == second
    assert first["review_packets"][0]["source_packet_id"] == second["review_packets"][0]["source_packet_id"]
    assert (tmp_path / "first" / "result.json").read_bytes() == (tmp_path / "second" / "result.json").read_bytes()


def test_archive_cannot_overwrite_existing_directory_or_enter_market_state(tmp_path):
    root = tmp_path / "scan"
    execute(root)
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    with pytest.raises(discovery.ReleaseDiscoveryError):
        execute(root)
    assert before == {p.name: p.read_bytes() for p in root.iterdir()}
    with pytest.raises(discovery.ReleaseDiscoveryError):
        execute(tmp_path / "decision-state" / "economic")


def test_injected_live_transport_and_future_baseline_are_rejected_before_network(tmp_path):
    with pytest.raises(discovery.ReleaseDiscoveryError, match="synthetic"):
        discovery.run_discovery(SOURCES, tmp_path / "live", transport=lambda url: pytest.fail("network"), now=lambda: NOW)
    with pytest.raises(discovery.ReleaseDiscoveryError, match="after the scan clock"):
        discovery.run_discovery(SOURCES, tmp_path / "future", transport=lambda url: pytest.fail("network"), provenance=discovery.SYNTHETIC, now=lambda: NOW - timedelta(days=1))


def test_lowest_transport_uses_only_explicit_urls_and_no_credential_headers(monkeypatch):
    calls = []
    class Remote:
        status = 200
        headers = {"Content-Type": "text/html; charset=utf-8", "Set-Cookie": "private"}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, n):
            assert n == discovery.MAX_BODY + 1
            return b"<html></html>"
        def geturl(self): return MOA
    class Opener:
        def open(self, request, timeout):
            calls.append((request.full_url, dict(request.header_items()), timeout))
            return Remote()
    monkeypatch.setattr(discovery, "build_opener", lambda *args: Opener())
    result = discovery.fetch_discovery_page(MOA)
    assert len(calls) == 1 and calls[0][2] == 20
    assert {key.lower() for key in calls[0][1]} == {"user-agent", "accept", "accept-encoding"}
    assert "set-cookie" not in result.headers
    with pytest.raises(discovery.ReleaseDiscoveryError):
        discovery.fetch_discovery_page("http://127.0.0.1/")
    assert len(calls) == 1
