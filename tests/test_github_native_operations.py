"""Native export mechanics and narrow maintenance boundaries, not a governance engine."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("workbench_source_bundle", ROOT / ".github/scripts/workbench-source-bundle.py")
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)


def inputs(sha="a" * 40):
    env = {"GITHUB_REPOSITORY": bundle.REPO, "GITHUB_EVENT_NAME": "workflow_dispatch",
           "GITHUB_REF": "refs/heads/main", "GITHUB_RUN_ATTEMPT": "1", "GITHUB_SHA": sha,
           "GITHUB_RUN_ID": "71", "GITHUB_WORKFLOW_REF": f"{bundle.REPO}/{bundle.WORKFLOW}@refs/heads/main"}
    main = {"ref": "refs/heads/main", "object": {"sha": sha}}
    run = {"id": 60, "path": ".github/workflows/ci.yml", "repository": {"full_name": bundle.REPO},
           "head_sha": sha, "head_branch": "main", "event": "push", "run_attempt": 1,
           "status": "completed", "conclusion": "success"}
    return env, main, {"workflow_runs": [run], "total_count": 1}


def test_bundle_qualified_latest_main_ci():
    env, main, runs = inputs()
    assert bundle.qualify(env, "a" * 40, main, runs)["run_id"] == 60


@pytest.mark.parametrize("key,value", [("GITHUB_REPOSITORY", "else/repo"),
    ("GITHUB_EVENT_NAME", "push"), ("GITHUB_REF", "refs/heads/draft"),
    ("GITHUB_RUN_ATTEMPT", "2"), ("GITHUB_WORKFLOW_REF", "other"), ("GITHUB_SHA", "b" * 40)])
def test_bundle_wrong_invocation_stops_before_output(tmp_path, key, value):
    env, main, runs = inputs()
    env[key] = value
    with pytest.raises(ValueError):
        bundle.build(tmp_path, tmp_path / "out", env, "a" * 40, main, runs)
    assert not (tmp_path / "out").exists()


def test_bundle_new_failed_attempt_never_falls_back_to_old_success():
    env, main, runs = inputs()
    runs["workflow_runs"].append(dict(runs["workflow_runs"][0], id=61, conclusion="failure"))
    with pytest.raises(ValueError, match="latest CI"):
        bundle.qualify(env, "a" * 40, main, runs)
    runs["workflow_runs"][-1].update(conclusion="success", run_attempt=2)
    with pytest.raises(ValueError, match="origin"):
        bundle.qualify(env, "a" * 40, main, runs)


def test_bundle_moved_main_or_empty_query_is_not_qualified():
    env, main, runs = inputs()
    main["object"]["sha"] = "b" * 40
    with pytest.raises(ValueError, match="advanced"):
        bundle.qualify(env, "a" * 40, main, runs)
    main["object"]["sha"] = "a" * 40
    with pytest.raises(ValueError, match="empty"):
        bundle.qualify(env, "a" * 40, main, {"workflow_runs": []})


def test_native_git_archive_exports_exact_commit_not_worktree_and_cannot_overwrite(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root, stderr=subprocess.DEVNULL).decode().strip()
    git("init")
    git("config", "user.name", "fixture")
    git("config", "user.email", "fixture@example.invalid")
    (root / "workbench").mkdir()
    (root / "workbench/app.mjs").write_text("export const source = 'committed';\n")
    (root / "docs").mkdir()
    (root / "docs/github-native-operations.md").write_text("Not a deployed site.\n")
    (root / "unrelated.txt").write_text("must not export\n")
    git("add", ".")
    git("commit", "-m", "synthetic source export")
    sha = git("rev-parse", "HEAD")
    (root / "workbench/app.mjs").write_text("uncommitted content must not leak")
    env, main, runs = inputs(sha)
    out = tmp_path / "out"
    result = bundle.build(root, out, env, sha, main, runs)
    raw = (out / "workbench-source.tar").read_bytes()
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        names = archive.getnames()
        assert bundle.PREFIX + "unrelated.txt" not in names
        assert archive.extractfile(bundle.PREFIX + "workbench/app.mjs").read() == b"export const source = 'committed';\n"
    commit = subprocess.check_output(["git", "get-tar-commit-id"], input=raw).decode().strip()
    assert commit == sha
    assert result["archive"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert result == json.loads((out / "source-manifest.json").read_text())
    assert result["site_adoption"] == "NOT_ESTABLISHED"
    with pytest.raises(FileExistsError):
        bundle.build(root, out, env, sha, main, runs)
    assert (out / "workbench-source.tar").read_bytes() == raw


def test_maintenance_is_independent_and_does_not_execute_sources():
    text = (ROOT / ".github/workflows/repository-security.yml").read_text()
    assert "workflow_dispatch:" in text and "schedule:" in text
    assert "build-mode: none" in text and "upload-database: false" in text
    assert "security-events: write" in text and "persist-credentials: false" in text
    for forbidden in ("pull_request:", "push:", "secrets.", "pip install", "npm install", "continue-on-error"):
        assert forbidden not in text


def test_bundle_workflow_signs_and_verifies_real_bytes_with_bound_identity():
    text = (ROOT / ".github/workflows/workbench-source-bundle.yml").read_text()
    for required in ("attestations: write", "id-token: write", "--source-ref refs/heads/main",
                     '--source-digest "$GITHUB_SHA"', "--signer-workflow", "--deny-self-hosted-runners",
                     'printf x >>', "TAMPERED_BYTES_REJECTED", "create-storage-record: false"):
        assert required in text
    for forbidden in ("schedule:", "push:", "pull_request:", "secrets.", "contents: write", "continue-on-error"):
        assert forbidden not in text


def test_dependabot_two_grouped_weekly_ecosystems_without_auto_merge():
    text = (ROOT / ".github/dependabot.yml").read_text()
    assert text.count("package-ecosystem:") == 2
    assert "package-ecosystem: pip" in text and "package-ecosystem: github-actions" in text
    assert text.count("interval: weekly") == text.count("open-pull-requests-limit: 1") == 2
    assert text.count("patterns: ['*']") == 2
    assert "ignore:" not in text and "insecure-external-code-execution" not in text
