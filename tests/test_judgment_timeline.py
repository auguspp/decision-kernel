from __future__ import annotations

import copy
import hashlib
import json
import shutil
import socket
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime.judgment_timeline import (
    DEFAULT_MANIFEST, SEMANTICS, build_judgment_timeline,
    main, render_judgment_timeline, write_judgment_timeline,
)

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 5, 15, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("readonly timeline attempted network access")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "source"
    spec = json.loads((ROOT / DEFAULT_MANIFEST).read_text(encoding="utf-8"))
    paths = [DEFAULT_MANIFEST] + [r["path"] for c in spec["cases"] for r in c["records"]]
    for relative in paths:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return root


def _edit(root, change):
    path = root / DEFAULT_MANIFEST
    spec = json.loads(path.read_text(encoding="utf-8"))
    change(spec)
    path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")


def _fingerprint(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


def test_pinned_real_checkpoints_and_exact_excerpts_are_preserved(source):
    before = _fingerprint(source)
    result = build_judgment_timeline(source, generated_at=NOW)
    p = result["projection"]
    assert p["semantics"] == SEMANTICS
    assert p["investment_authority"] == "NONE"
    assert p["creates_canonical_wake"] is False
    assert result["projection_hash"] == canonical_hash(p)
    assert len(p["cases"]) == 3
    assert sum(len(c["records"]) for c in p["cases"]) == 4
    for case in p["cases"]:
        for record in case["records"]:
            raw = (source / record["path"]).read_bytes()
            assert record["sha256"] == hashlib.sha256(raw).hexdigest()
            assert record["blob_sha1"] == hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            lines = raw.decode().splitlines(keepends=True)
            for excerpt in [record["clock"], record["human_quote"], *(n["source"] for n in record["panels"])]:
                start, end = excerpt["lines"]
                assert excerpt["text"] == "".join(lines[start - 1:end])
                assert f'/blob/{p["source_commit"]}/' in excerpt["url"]
                assert excerpt["url"].endswith(f"#L{start}-L{end}")
    assert _fingerprint(source) == before


def test_three_distinct_human_meanings_are_not_reclassified(source):
    p = build_judgment_timeline(source, generated_at=NOW)["projection"]
    catl, sanhua, micron = p["cases"]
    assert "没有 BUY／SELL／HOLD 决定" in catl["records"][0]["panels"][1]["navigation_note"]
    original, supplement = sanhua["records"]
    assert "NOT YET SPECIFIED" in original["panels"][3]["source"]["text"]
    assert "after actual execution" in supplement["panels"][0]["source"]["text"]
    assert supplement["parent"] == original["path"]
    assert "NO_ACTION != NEGATIVE FUNDAMENTAL BELIEF" in micron["records"][0]["panels"][1]["source"]["text"]
    assert "OBSERVEDMARKET = NOT AVAILABLE" in micron["records"][0]["panels"][0]["source"]["text"]
    assert "2026-09-03 conversation PIT" in micron["records"][0]["clock"]["text"]
    assert "00:00" not in micron["records"][0]["clock"]["text"]


def test_generation_time_never_settles_or_rewrites_record_clocks(source):
    old = build_judgment_timeline(source, generated_at=NOW)
    later = build_judgment_timeline(source, generated_at=NOW + timedelta(days=800))
    assert old["generated_at"] != later["generated_at"]
    assert old["projection"] == later["projection"]
    assert old["projection_hash"] == later["projection_hash"]
    assert set(old) == {"generated_at", "projection", "projection_hash"}
    assert "不按今天日期自动结算" in later["projection"]["outcome_notice"]


def test_native_page_has_no_telemetry_forms_scripts_or_price_chart(source):
    report = build_judgment_timeline(source, generated_at=NOW)
    page = BeautifulSoup(render_judgment_timeline(report), "html.parser")
    assert page.html["lang"] == "zh-CN"
    assert not page.select("script, iframe, form, input, button, img, link, canvas, svg")
    assert len(page.select("article.record")) == 4
    assert len(page.select("blockquote")) == 4
    assert all(not d.has_attr("open") for d in page.select("details"))
    assert "default-src 'none'" in page.find("meta", attrs={"http-equiv": "Content-Security-Policy"})["content"]
    assert "页面生成时间" in page.get_text()
    assert "不是行情或判断时间" in page.get_text()
    assert "不能认定为独立 Human forecast" in page.get_text()
    for a in page.select("a[href]"):
        assert a["href"].startswith(("#", "https://github.com/auguspp/decision-kernel/blob/")) or a["href"] == "projection.json"


def test_navigation_text_is_escaped_not_interpreted(source):
    _edit(source, lambda s: s["cases"][0].update(label='<script>alert("x")</script>'))
    report = build_judgment_timeline(source, generated_at=NOW)
    page = BeautifulSoup(render_judgment_timeline(report), "html.parser")
    assert not page.select("script")
    assert '<script>alert("x")</script>' in page.get_text()


@pytest.mark.parametrize("span", [[0, 1], [2, 1], [1, 99999], [True, 5], [1], "1:5"])
def test_invalid_line_ranges_rejected(source, span):
    _edit(source, lambda s: s["cases"][0]["records"][0].update(clock=span))
    with pytest.raises(ValueError, match="span"):
        build_judgment_timeline(source, generated_at=NOW)


@pytest.mark.parametrize("path", ["/etc/passwd", "docs/../escape.md", "docs/./file.md", "docs\\file.md"])
def test_noncanonical_source_paths_rejected(source, path):
    _edit(source, lambda s: s["cases"][0]["records"][0].update(path=path))
    with pytest.raises(ValueError):
        build_judgment_timeline(source, generated_at=NOW)


def test_source_drift_fails_without_creating_output(source, tmp_path):
    path = next((source / "docs").rglob("*.md"))
    path.write_bytes(path.read_bytes() + b"\n")
    stdout, stderr = StringIO(), StringIO()
    out = tmp_path / "output"
    assert main(["--source-root", str(source), "--output", str(out)], stdout=stdout, stderr=stderr) == 2
    assert stdout.getvalue() == ""
    assert "identity changed" in stderr.getvalue()
    assert not out.exists()


def test_symlink_source_rejected(source, tmp_path):
    path = next((source / "docs").rglob("*.md"))
    target = tmp_path / "external.md"
    target.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(target)
    with pytest.raises(ValueError, match="symbolic links"):
        build_judgment_timeline(source, generated_at=NOW)


@pytest.mark.parametrize("mutation", ["branch", "extra-authority", "duplicate-record", "duplicate-case", "unlinked-parent"])
def test_invalid_view_manifest_not_promoted(source, mutation):
    def change(s):
        if mutation == "branch": s["source_commit"] = "main"
        elif mutation == "extra-authority": s["investment_authority"] = "EXECUTE"
        elif mutation == "duplicate-record": s["cases"][0]["records"] *= 2
        elif mutation == "duplicate-case": s["cases"].append(copy.deepcopy(s["cases"][0]))
        else: s["cases"][0]["records"][0]["parent"] = "docs/decisions/other.md"
    _edit(source, change)
    with pytest.raises(ValueError):
        build_judgment_timeline(source, generated_at=NOW)


def test_duplicate_json_keys_and_naive_generation_clock_rejected(source):
    with pytest.raises(ValueError, match="timezone-aware"):
        build_judgment_timeline(source, generated_at=NOW.replace(tzinfo=None))
    (source / DEFAULT_MANIFEST).write_text('{"view_version":1,"view_version":1}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        build_judgment_timeline(source, generated_at=NOW)


def test_hash_and_authority_tampering_rejected(source):
    report = build_judgment_timeline(source, generated_at=NOW)
    report["projection"]["investment_authority"] = "EXECUTE"
    with pytest.raises(ValueError): render_judgment_timeline(report)
    report["projection_hash"] = canonical_hash(report["projection"])
    with pytest.raises(ValueError): render_judgment_timeline(report)


def test_writer_only_creates_new_external_display_files(source, tmp_path):
    before = _fingerprint(source)
    report = build_judgment_timeline(source, generated_at=NOW)
    with pytest.raises(ValueError):
        write_judgment_timeline(report, source / "output", source_root=source)
    out = tmp_path / "output"
    write_judgment_timeline(report, out, source_root=source)
    assert set(p.name for p in out.iterdir()) == {"index.html", "projection.json"}
    assert json.loads((out / "projection.json").read_text(encoding="utf-8")) == report
    with pytest.raises(ValueError):
        write_judgment_timeline(report, out, source_root=source)
    assert _fingerprint(source) == before


def test_partial_display_write_is_cleaned_up(source, tmp_path, monkeypatch):
    report = build_judgment_timeline(source, generated_at=NOW)
    original = Path.open
    def fail(self, *args, **kwargs):
        if self.name == "projection.json":
            raise OSError("simulated display write failure")
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Path, "open", fail)
    out = tmp_path / "output"
    with pytest.raises(OSError): write_judgment_timeline(report, out, source_root=source)
    assert not out.exists()
