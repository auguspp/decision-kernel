from __future__ import annotations

import ast
import json
import platform
import tomllib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import economic_release_discovery as discovery


NOW = datetime(2026, 9, 5, 12, tzinfo=timezone.utc)
SOURCES = json.loads(Path("radar_inputs/economic-node-study-2026-09-05.json").read_text(encoding="utf-8"))
MOA_URL = discovery.DIRECTORIES["MOA_FEED"]
ARTICLE = SOURCES[1]["source_url"]
TITLE = SOURCES[1]["title"]
DAY = SOURCES[1]["published_date"]


def response(url, markup):
    body = markup.encode("utf-8")
    return discovery.PublicResponse(url, 200, {"content-type": "text/html; charset=utf-8"}, body)


def row(url=ARTICLE, title=TITLE, day=DAY):
    return f'<li><a href="{url}" title="{title}">{title}</a><span>{day}</span></li>'


def parse(markup):
    return discovery.parse_directory("MOA_FEED", response(MOA_URL, markup), captured_at=NOW)


def execute(root, monkeypatch=None):
    responses = {
        MOA_URL: response(MOA_URL, row()),
        discovery.DIRECTORIES["SPB_EXPRESS"]: response(discovery.DIRECTORIES["SPB_EXPRESS"],
            row(SOURCES[3]["source_url"], SOURCES[3]["title"], SOURCES[3]["published_date"])),
    }
    ticks = iter(NOW + timedelta(seconds=i) for i in range(20))
    return discovery.run_discovery(SOURCES, root, transport=responses.__getitem__,
                                   provenance=discovery.SYNTHETIC, now=lambda: next(ticks))


def test_no_second_handwritten_directory_or_metadata_parser():
    tree = ast.parse(Path(discovery.__file__).read_text(encoding="utf-8"))
    names = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
    assert names == {"ReleaseDiscoveryError"}
    assert isinstance(discovery._soup(response(MOA_URL, row())), BeautifulSoup)
    assert discovery._parser_runtime() == {
        "beautifulsoup4": "4.14.3", "builder": "html.parser", "python": platform.python_version(),
    }


def test_optional_dependency_does_not_enter_the_kernel_base_environment():
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]
    pin = "beautifulsoup4==4.14.3"
    assert pin not in project["dependencies"]
    assert project["optional-dependencies"]["discovery"] == [pin]
    assert pin in project["optional-dependencies"]["dev"]
    assert discovery.DIRECTORIES["SPB_EXPRESS"] == "https://www.spb.gov.cn/gjyzj/c100275/pubtz.shtml"


def test_library_source_positions_and_decoded_entities_are_retained():
    markup = '\n<ul>\n  <li> <a href="' + ARTICLE + '">' + TITLE + '</a><span>' + DAY + '</span></li>\n</ul>'
    observed = parse(markup)["rows"][0]
    assert observed["source_url"] == ARTICLE
    assert (observed["anchor_line"], observed["anchor_column"]) == (3, 7)
    assert observed["directory_body_sha256"] == discovery._sha(markup.encode("utf-8"))
    assert observed["listed_publication_date"] == DAY


@pytest.mark.parametrize("attribute", [f'href="{ARTICLE}"', f'title="{TITLE}"'])
def test_duplicate_source_attributes_are_not_silently_normalized(attribute):
    markup = row().replace(f'<a href="{ARTICLE}" title="{TITLE}"',
                           f'<a href="{ARTICLE}" title="{TITLE}" {attribute}')
    with pytest.raises(discovery.ReleaseDiscoveryError, match="duplicate"):
        parse(markup)


def test_dates_cannot_be_borrowed_from_nested_rows():
    markup = '<li><a href="' + ARTICLE + '">' + TITLE + '</a><ul><li>' + DAY + '</li></ul></li>'
    with pytest.raises(discovery.ReleaseDiscoveryError, match="full date"):
        parse(markup)


def test_nested_or_ambiguous_anchors_still_fail():
    for markup in (
        row().replace('</a>', '<a href="' + ARTICLE + '">nested</a></a>'),
        row().replace('</a>', '</a><a href="' + ARTICLE + '">duplicate</a>'),
    ):
        with pytest.raises(discovery.ReleaseDiscoveryError):
            parse(markup)


@pytest.mark.parametrize("ignored", ["script", "style", "template", "noscript"])
def test_inert_template_and_script_content_cannot_supply_rows(ignored):
    markup = row() + f'<{ignored}>' + row(day="2099-01-01") + f'</{ignored}>'
    assert len(parse(markup)["rows"]) == 1


def test_base_url_cannot_change_the_requested_source_family():
    with pytest.raises(discovery.ReleaseDiscoveryError, match="base URL"):
        parse('<base href="https://unreviewed.invalid/">' + row())


def test_missing_or_wrong_parser_fails_before_requests_and_archive_creation(tmp_path, monkeypatch):
    def absent(name):
        raise discovery.PackageNotFoundError(name)
    for provider in (absent, lambda name: "0.0.0"):
        monkeypatch.setattr(discovery, "version", provider)
        with pytest.raises(discovery.ReleaseDiscoveryError):
            discovery.run_discovery(SOURCES, tmp_path / "absent", provenance=discovery.SYNTHETIC,
                                   transport=lambda url: pytest.fail("no network"), now=lambda: NOW)
        assert not (tmp_path / "absent").exists()


@pytest.mark.parametrize("field", ["parser_runtime", "schema_version"])
def test_parser_runtime_and_old_schema_cannot_be_relabelled_by_rehashing(tmp_path, field):
    root = tmp_path / "scan"
    execute(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["parser_runtime"] == discovery._parser_runtime()
    manifest[field] = {"beautifulsoup4": "0.0.0"} if field == "parser_runtime" else 1
    manifest.pop("archive_hash")
    manifest["archive_hash"] = canonical_hash(manifest)
    (root / "manifest.json").write_bytes(discovery._bytes(manifest))
    with pytest.raises(discovery.ReleaseDiscoveryError, match="identity/hash/implementation"):
        discovery.verify_discovery(root)


def test_statistics_window_does_not_change_review_authority_or_claim_complete_coverage(tmp_path):
    root = tmp_path / "scan"
    result = execute(root)
    assert result["plan"]["detail_requests"] == []
    assert not result["complete_publisher_coverage"]
    assert not result["automatic_review_acceptance"]
    assert result["observation_writes"] == result["market_event_writes"] == 0
    assert discovery.verify_discovery(root)["network_calls"] == 0
    assert all(item["discovery_disposition"] == "KNOWN_URL_NOT_REVALIDATED" for item in result["plan"]["entries"])
