from __future__ import annotations

import hashlib
import json
import runpy
import shutil
import subprocess
from datetime import timedelta
from pathlib import Path

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime.judgment_timeline import DEFAULT_MANIFEST
from test_judgment_timeline import NOW, ROOT, no_network, source  # reuse existing fixtures

SCRIPT = ROOT / ".github/scripts/build-judgment-timeline.py"
MODULE = runpy.run_path(str(SCRIPT))
deliver = MODULE["build_ci_delivery"]


def git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
         "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
        check=True, capture_output=True,
    ).stdout.decode().strip()


def commit(root):
    git(root, "add", ".")
    git(root, "commit", "-qm", "synthetic local-history fixture; no network")
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def checkout(source):
    for relative in MODULE["BUILD_FILES"]:
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    git(source, "init", "-q")
    pin = commit(source)
    manifest = source / DEFAULT_MANIFEST
    spec = json.loads(manifest.read_text(encoding="utf-8"))
    spec["source_commit"] = pin
    manifest.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    head = commit(source)
    env = {"GITHUB_REPOSITORY": "auguspp/decision-kernel", "GITHUB_EVENT_NAME": "push",
           "GITHUB_REF": "refs/heads/main", "GITHUB_WORKFLOW": "kernel-tests",
           "GITHUB_SHA": head, "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1",
           "GITHUB_TOKEN": "must-not-be-recorded", "HITHINK_FINANCE_API_KEY": "also-private"}
    return source, env


def test_delivery_copies_exact_sources_and_binds_distinct_build_and_source_commits(checkout, tmp_path):
    root, env = checkout
    before = git(root, "status", "--porcelain")
    out = tmp_path / "delivery"
    receipt = deliver(root, out, environ=env, generated_at=NOW)
    assert receipt["build_commit"] == env["GITHUB_SHA"]
    assert receipt["source_commit"] != receipt["build_commit"]
    assert receipt["records_human_exposure"] is False
    assert receipt["creates_canonical_wake"] is False
    assert receipt["investment_authority"] == "NONE"
    assert set(receipt["build_inputs"]) == set(MODULE["BUILD_FILES"])
    files = {str(p.relative_to(out)) for p in out.rglob("*") if p.is_file()}
    assert len(files) == 9
    assert files == set(receipt["files"]) | {"build.json"}
    for relative, info in receipt["files"].items():
        raw = (out / relative).read_bytes()
        assert info == {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        if relative.startswith("sources/"):
            assert raw == (root / relative.removeprefix("sources/")).read_bytes()
    saved = json.loads((out / "build.json").read_text(encoding="utf-8"))
    assert saved == receipt
    recorded_hash = saved.pop("build_hash")
    assert canonical_hash(saved) == recorded_hash
    assert "must-not-be-recorded" not in json.dumps(receipt)
    assert "also-private" not in json.dumps(receipt)
    assert git(root, "status", "--porcelain") == before == ""


def test_later_build_and_attempt_never_create_a_new_judgment(checkout, tmp_path):
    root, env = checkout
    first = deliver(root, tmp_path / "first", environ=env, generated_at=NOW)
    second = deliver(root, tmp_path / "second", environ={**env, "GITHUB_RUN_ATTEMPT": "2"}, generated_at=NOW + timedelta(days=800))
    assert first["projection_hash"] == second["projection_hash"]
    assert first["build_hash"] != second["build_hash"]
    for name in ("first", "second"):
        p = json.loads((tmp_path / name / "projection.json").read_text(encoding="utf-8"))["projection"]
        assert "不按今天日期自动结算" in p["outcome_notice"]
        assert p["creates_canonical_wake"] is False


@pytest.mark.parametrize("key,value", [
    ("GITHUB_EVENT_NAME", "pull_request"), ("GITHUB_EVENT_NAME", "workflow_dispatch"),
    ("GITHUB_REF", "refs/heads/feature"), ("GITHUB_REPOSITORY", "other/repo"),
    ("GITHUB_WORKFLOW", "other"), ("GITHUB_RUN_ID", "../1"),
    ("GITHUB_RUN_ATTEMPT", "0"), ("GITHUB_SHA", "a" * 40),
])
def test_wrong_context_never_writes_a_delivery(checkout, tmp_path, key, value):
    root, env = checkout
    out = tmp_path / "delivery"
    with pytest.raises(ValueError):
        deliver(root, out, environ={**env, key: value}, generated_at=NOW)
    assert not out.exists()


@pytest.mark.parametrize("relative", [DEFAULT_MANIFEST, ".github/scripts/build-judgment-timeline.py"])
def test_dirty_build_input_is_not_published_under_a_clean_commit(checkout, tmp_path, relative):
    root, env = checkout
    path = root / relative
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="build input differs"):
        deliver(root, tmp_path / "delivery", environ=env, generated_at=NOW)
    assert not (tmp_path / "delivery").exists()


@pytest.mark.parametrize("pin", ["missing", "wrong-file"])
def test_source_commit_must_really_contain_the_selected_bytes(checkout, tmp_path, pin):
    root, env = checkout
    manifest = root / DEFAULT_MANIFEST
    spec = json.loads(manifest.read_text(encoding="utf-8"))
    if pin == "missing":
        spec["source_commit"] = "a" * 40
    else:
        source_path = root / spec["cases"][0]["records"][0]["path"]
        original = source_path.read_bytes()
        source_path.write_bytes(original + b"\nwrong historical bytes")
        spec["source_commit"] = commit(root)
        source_path.write_bytes(original)
    manifest.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    env["GITHUB_SHA"] = commit(root)
    with pytest.raises(ValueError, match="local Git identity|declared source commit"):
        deliver(root, tmp_path / "delivery", environ=env, generated_at=NOW)
    assert not (tmp_path / "delivery").exists()


def test_output_tampering_before_verification_cleans_owned_directory(checkout, tmp_path, monkeypatch):
    root, env = checkout
    original = deliver.__globals__["write_judgment_timeline"]
    def altered(report, output, *, source_root):
        original(report, output, source_root=source_root)
        (output / "index.html").write_text("stale page", encoding="utf-8")
    monkeypatch.setitem(deliver.__globals__, "write_judgment_timeline", altered)
    with pytest.raises(ValueError, match="disagree"):
        deliver(root, tmp_path / "delivery", environ=env, generated_at=NOW)
    assert not (tmp_path / "delivery").exists()


def test_receipt_write_failure_is_not_a_publishable_partial_bundle(checkout, tmp_path, monkeypatch):
    root, env = checkout
    original = Path.write_text
    def failed(path, *args, **kwargs):
        if path.name == "build.json":
            raise OSError("simulated receipt write failure")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "write_text", failed)
    with pytest.raises(OSError):
        deliver(root, tmp_path / "delivery", environ=env, generated_at=NOW)
    assert not (tmp_path / "delivery").exists()


def test_existing_output_is_never_deleted(checkout, tmp_path):
    root, env = checkout
    out = tmp_path / "existing"
    out.mkdir()
    marker = out / "keep"
    marker.write_text("owned by another operation", encoding="utf-8")
    with pytest.raises(ValueError):
        deliver(root, out, environ=env, generated_at=NOW)
    assert marker.read_text(encoding="utf-8") == "owned by another operation"


def test_existing_ci_delivery_is_main_only_secret_free_and_success_gated():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    job = workflow.split("  judgment-timeline:", 1)[1]
    assert "needs: test" in job
    assert "github.event_name == 'push'" in job and "github.ref == 'refs/heads/main'" in job
    assert "contents: read" in job and "persist-credentials: false" in job
    assert "fetch-depth: 0" in job and "fetch-tags: false" in job
    assert "actions/upload-artifact@v7" in job and "if-no-files-found: error" in job
    assert "retention-days: 30" in job
    assert "name: judgment-timeline-${{ github.run_id }}-${{ github.run_attempt }}" in job
    assert "secrets." not in job and "actions/cache" not in job
    assert "workflow_dispatch" not in workflow and "schedule:" not in workflow
    assert "continue-on-error" not in job and "overwrite: true" not in job
    assert '[ "$BUILD_OUTCOME" = \'success\' ] && [ "$UPLOAD_OUTCOME" = \'success\' ]' in job
    assert "steps.timeline-upload.outputs.artifact-url" in job
    assert "没有读取新行情、自动结算或记录 Human 阅读／同意" in job
