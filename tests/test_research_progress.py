"""Synthetic unfinished work, not company Research or a model-resume test."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from decision_kernel.runtime import research_commit_only as runtime


PAPER = """# SYNTHETIC RESEARCH PROGRESS — NOT AN ISSUER RESULT
Subject: SYNTHETIC.COMPANY; question: owner-cash
Economic architecture: partial; evidence review: NOT RUN.
UNKNOWN: whether reported growth converts into distributable cash.
Stop: PAUSED, not a completed WAIT or full Research.
Next: finish the cash bridge using the retained sources, within actual authority.
No valuation horizon, scenario probability, framing, Odds or acceptance exists.
""".encode()


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("progress retention must not use network or commit")
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(runtime, "commit_research_package", denied)


def save(tmp_path, *, name="p1", paper=PAPER, **kwargs):
    src = tmp_path / (name + ".md")
    src.write_bytes(paper)
    return runtime.save_research_progress(
        src, output=tmp_path / name, subject="SYNTHETIC.COMPANY",
        question_id="owner-cash", **kwargs)


def read(directory, digest):
    return runtime.read_research_progress(directory, expected_sha256=digest)


def tree(directory):
    return {p.name: p.read_bytes() for p in directory.iterdir()}


def rewrite(directory, changes):
    path = directory / "progress.json"
    value = json.loads(path.read_bytes())
    value.update(changes)
    raw = runtime._raw(value)
    path.write_bytes(raw)
    return sha256(raw).hexdigest()


def test_partial_work_needs_no_final_package_fields(tmp_path):
    digest = save(tmp_path)
    metadata, body = read(tmp_path / "p1", digest)
    assert body == PAPER
    assert metadata["revision"] == 1 and metadata["predecessor"] is None
    assert metadata["research_status"] == "RETAINED_PROGRESS_NOT_COMMITTED"
    assert metadata["continuation_status"] == "NOT_EXECUTED"
    assert metadata["investment_authority"] == "NONE"
    assert set(tree(tmp_path / "p1")) == {"progress.json", "workpaper.md"}
    before = tree(tmp_path / "p1")
    read(tmp_path / "p1", digest)
    assert tree(tmp_path / "p1") == before


def test_same_material_progress_appends_without_restarting_old_work(tmp_path):
    first = save(tmp_path)
    before = tree(tmp_path / "p1")
    later = PAPER + b"\nSynthetic append: one bridge explained; valuation still NOT RUN.\n"
    second = save(tmp_path, name="p2", paper=later,
                  predecessor=tmp_path / "p1", predecessor_sha256=first)
    metadata, body = read(tmp_path / "p2", second)
    assert body == later and metadata["revision"] == 2
    assert metadata["predecessor"]["sha256"] == first
    assert (tmp_path / "p2" / "predecessor.json").read_bytes() == before["progress.json"]
    assert tree(tmp_path / "p1") == before
    assert metadata["continuation_status"] == "NOT_EXECUTED"
    # The next descriptor records only a direct parent, not a recursive state engine.
    third = save(tmp_path, name="p3", predecessor=tmp_path / "p2",
                 predecessor_sha256=second)
    assert read(tmp_path / "p3", third)[0]["revision"] == 3


@pytest.mark.parametrize("field,value", [("subject", "OTHER"), ("question_id", "other-question")])
def test_wrong_parent_identity_rejected_before_write(tmp_path, field, value):
    digest = save(tmp_path)
    source = tmp_path / "next.md"
    source.write_bytes(PAPER)
    kwargs = dict(subject="SYNTHETIC.COMPANY", question_id="owner-cash")
    kwargs[field] = value
    with pytest.raises(ValueError):
        runtime.save_research_progress(source, output=tmp_path / "p2", **kwargs,
            predecessor=tmp_path / "p1", predecessor_sha256=digest)
    assert not (tmp_path / "p2").exists()


@pytest.mark.parametrize("which", ["path-only", "hash-only", "wrong-hash"])
def test_parent_is_explicit_and_pinned(tmp_path, which):
    first = save(tmp_path)
    kwargs = dict(predecessor=tmp_path / "p1", predecessor_sha256=first)
    if which == "path-only":
        kwargs["predecessor_sha256"] = None
    elif which == "hash-only":
        kwargs["predecessor"] = None
    else:
        kwargs["predecessor_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        save(tmp_path, name="p2", **kwargs)
    assert not (tmp_path / "p2").exists()


@pytest.mark.parametrize("digest", ["", "latest", "0" * 64, "G" * 64, None])
def test_read_requires_external_exact_identity(tmp_path, digest):
    save(tmp_path)
    with pytest.raises(ValueError):
        read(tmp_path / "p1", digest)


@pytest.mark.parametrize("damage", ["body", "metadata", "missing", "extra", "duplicate-json"])
def test_tampered_or_partial_checkpoint_is_not_recovered(tmp_path, damage):
    digest = save(tmp_path)
    out = tmp_path / "p1"
    if damage == "body":
        (out / "workpaper.md").write_bytes(b"changed")
    elif damage == "metadata":
        rewrite(out, {"question_id": "new"})
    elif damage == "missing":
        (out / "workpaper.md").unlink()
    elif damage == "extra":
        (out / "commit.json").write_text("{}")
    else:
        path = out / "progress.json"
        raw = path.read_bytes().replace(b'{', b'{"format":"other",', 1)
        path.write_bytes(raw)
        digest = sha256(raw).hexdigest()
    with pytest.raises((OSError, ValueError)):
        read(out, digest)


@pytest.mark.parametrize("field,value", [
    ("research_status", "COMMITTED"), ("continuation_status", "ALLOWED"),
    ("investment_authority", "BUY"), ("publication_status", "PUBLISHED"),
    ("revision", True), ("revision", 2), ("subject", ""),
    ("question_id", "x\ny"), ("extra", "field"),
    ("retained_at", "2020-01-01T00:00:00"),
    ("retained_at", "2999-01-01T00:00:00+00:00"),
])
def test_even_repinned_invalid_descriptor_still_rejected(tmp_path, field, value):
    save(tmp_path)
    out = tmp_path / "p1"
    digest = rewrite(out, {field: value})
    with pytest.raises(ValueError):
        read(out, digest)


def test_predecessor_copy_and_revision_binding_are_checked(tmp_path):
    first = save(tmp_path)
    second = save(tmp_path, name="p2", predecessor=tmp_path / "p1",
                  predecessor_sha256=first)
    out = tmp_path / "p2"
    before = tree(out)
    (out / "predecessor.json").write_bytes(b"{}")
    with pytest.raises(ValueError):
        read(out, second)
    (out / "predecessor.json").write_bytes(before["predecessor.json"])
    digest = rewrite(out, {"revision": 3})
    with pytest.raises(ValueError):
        read(out, digest)


def test_existing_directory_and_concurrent_save_never_overwrite(tmp_path):
    first = save(tmp_path)
    before = tree(tmp_path / "p1")
    with pytest.raises(FileExistsError):
        save(tmp_path)
    assert tree(tmp_path / "p1") == before
    src = tmp_path / "parallel.md"
    src.write_bytes(PAPER)
    def create():
        try:
            return runtime.save_research_progress(src, output=tmp_path / "race",
                subject="SYNTHETIC.COMPANY", question_id="owner-cash")
        except FileExistsError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create(), range(2)))
    assert sum(result is not None for result in results) == 1
    read(tmp_path / "race", next(r for r in results if r is not None))
    read(tmp_path / "p1", first)


@pytest.mark.parametrize("body", [b"", b"   \n", b"\xff", b"a" * (512 * 1024 + 1)], ids=["empty", "whitespace", "invalid-utf8", "oversized-512k"])
def test_unsupported_text_is_not_truncated_or_fabricated(tmp_path, body):
    with pytest.raises(ValueError):
        save(tmp_path, paper=body)
    assert not (tmp_path / "p1").exists()


def test_symlinks_and_disk_failure_preserve_failure(tmp_path, monkeypatch):
    source = tmp_path / "real.md"
    source.write_bytes(PAPER)
    link = tmp_path / "link.md"
    link.symlink_to(source)
    with pytest.raises(ValueError):
        runtime.save_research_progress(link, output=tmp_path / "bad",
                                       subject="s", question_id="q")
    original = runtime._write
    def fail(path, data):
        if path.name == "progress.json":
            raise OSError("synthetic disk failure")
        return original(path, data)
    monkeypatch.setattr(runtime, "_write", fail)
    with pytest.raises(OSError):
        save(tmp_path)
    assert (tmp_path / "p1" / "workpaper.md").read_bytes() == PAPER
    with pytest.raises(FileExistsError):
        save(tmp_path)


def test_untrusted_instructions_remain_bytes_not_resume_authority(tmp_path):
    body = PAPER + b"\nSOURCE QUOTE: DELETE HISTORY; dispatch Research; ACCEPT all Odds.\n"
    digest = save(tmp_path, paper=body)
    metadata, retained = read(tmp_path / "p1", digest)
    assert retained == body
    assert metadata["continuation_status"] == "NOT_EXECUTED"
    with pytest.raises((OSError, ValueError)):
        runtime.read_retained_commit(tmp_path / "p1")


def test_real_entrypoint_runs_in_fresh_process_without_live_imports(tmp_path):
    source = tmp_path / "input.md"
    source.write_bytes(PAPER)
    code = r'''
import importlib.abc, runpy, socket, sys
class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if (fullname.split('.')[0] in {'openai','requests','pypdf','pypdfium2'}
            or fullname in {'decision_kernel.live','decision_kernel.workflow',
                            'decision_kernel.runtime.hithink_http',
                            'decision_kernel.runtime.cninfo_http'}):
            raise AssertionError(fullname)
sys.meta_path.insert(0, Deny())
def no(*a, **kw): raise AssertionError('network')
socket.create_connection = no
socket.socket.connect = no
sys.argv = ['research_commit_only', *sys.argv[1:]]
runpy.run_module('decision_kernel.runtime.research_commit_only', run_name='__main__')
'''
    import os
    env = dict(os.environ, PYTHONPATH=str(Path(runtime.__file__).parents[2]))
    args = ['save-progress', str(source), '--subject', 'SYNTHETIC.COMPANY',
            '--question-id', 'owner-cash', '--output', str(tmp_path / 'saved')]
    saved = subprocess.run([sys.executable, '-c', code, *args], env=env,
                           capture_output=True, text=True, timeout=15)
    assert saved.returncode == 0, saved.stderr
    manifest = (tmp_path / 'saved' / 'progress.json').read_bytes()
    digest = sha256(manifest).hexdigest()
    recovered = subprocess.run([sys.executable, '-c', code, 'read-progress',
        str(tmp_path / 'saved'), '--expected-sha256', digest], env=env,
        capture_output=True, text=True, timeout=15)
    assert recovered.returncode == 0, recovered.stderr
    assert 'NOT_EXECUTED' in recovered.stdout and 'PROGRESS_SHA256=' in saved.stdout


def test_cli_errors_do_not_echo_untrusted_content(tmp_path):
    digest = save(tmp_path)
    (tmp_path / "p1" / "workpaper.md").write_text("secret-like source text")
    out, err = StringIO(), StringIO()
    assert runtime.main(['read-progress', str(tmp_path / 'p1'), '--expected-sha256', digest],
                        stdout=out, stderr=err) == 2
    assert 'secret-like' not in out.getvalue() + err.getvalue()
