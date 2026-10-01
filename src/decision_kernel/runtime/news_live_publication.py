"""Publish one verified rolling News snapshot to an ephemeral read-only Git ref.

The ref is a latest-value delivery cache for Sites, not a source archive, Research
state, or complete-news claim. Exact source artifacts remain owned by the native
News workflow and the low-frequency current-state reading.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import copy

import requests

from ..identity import canonical_hash
from . import current_state as m
from . import current_state_delivery as delivery
from . import external_radar_observations as news
from . import news_daily as source

REF = "read-model/news-live"
MANIFEST = "news-live.json"
HISTORY = source.HISTORY_FILE
VERSION = "news-live-reading-v1"
SEMANTICS = "LATEST_VERIFIED_NEWS_CAPTURE_AND_ROLLING_INDEX_NOT_RESEARCH_OR_COMPLETE_NEWS"
CACHE_MEANING = "LATEST_ONLY_FORCE_UPDATED_DELIVERY_CACHE_NOT_SOURCE_ARCHIVE"
MAX_FILES = 32


def now():
    return datetime.now(timezone.utc).isoformat()


class NewsLiveGitHubAPI(delivery.GitHubAPI):
    """Existing transport with writes narrowed to the single ephemeral News ref."""

    def _call(self, method: str, endpoint: str, body=None):
        m.check(not endpoint.startswith("/") and ".." not in endpoint and "://" not in endpoint,
                "invalid API endpoint")
        if method != "GET":
            m.check((method == "POST" and endpoint in {"git/blobs", "git/trees", "git/commits", "git/refs"})
                    or (method == "PATCH" and endpoint == "git/refs/heads/" + REF),
                    "write outside News live Git objects rejected")
            if endpoint == "git/refs":
                m.check(body.get("ref") == "refs/heads/" + REF, "wrong News live publication ref")
            if method == "PATCH":
                m.check(body == {"sha": body.get("sha"), "force": True}
                        and m.SHA.fullmatch(body.get("sha", "")) is not None,
                        "News live update must be one exact force pointer move")
        self.calls += 1
        m.check(self.calls <= self.max_calls, "GitHub request budget exhausted")
        try:
            response = self.session.request(method, self.root + endpoint, json=body,
                                            timeout=45, allow_redirects=False)
        except requests.RequestException as exc:
            raise delivery.GitHubReadError("GitHub transport unavailable") from exc
        if response.status_code not in {200, 201, 302}:
            raise delivery.GitHubReadError("GitHub HTTP " + str(response.status_code))
        return response

    def fresh_get(self, endpoint: str):
        response = self._call("GET", endpoint)
        m.check(len(response.content) <= 8 * 1024 * 1024, "GitHub JSON response limit")
        return response.json()

    def file(self, path: str, ref: str) -> bytes:
        """Read only the two live files via commit -> tree -> bounded Git blob.

        Contents JSON omits bodies above 1 MB; rolling history permits 2 MiB.
        Reuse the existing authenticated, no-redirect, no-retry transport without
        changing current-state's implementation or following a response URL.
        """
        m.check(path in {MANIFEST, HISTORY}, "News live read path outside scope")
        m.check(isinstance(ref, str) and m.SHA.fullmatch(ref) is not None,
                "News live file requires exact commit")
        saved = self.get("git/commits/" + ref)
        tree_sha = saved.get("tree", {}).get("sha", "")
        m.check(saved.get("sha") == ref and m.SHA.fullmatch(tree_sha) is not None,
                "News live commit identity differs")
        tree = self.get("git/trees/" + tree_sha)
        entries = tree.get("tree")
        m.check(tree.get("sha") == tree_sha and tree.get("truncated") is False
                and isinstance(entries, list) and len(entries) == 2
                and {entry.get("path") for entry in entries} == {MANIFEST, HISTORY},
                "News live tree inventory differs")
        entry = next(row for row in entries if row["path"] == path)
        size, sha = entry.get("size"), entry.get("sha", "")
        limit = source.MAX_HISTORY_BYTES if path == HISTORY else 192 * 1024
        m.check(entry.get("type") == "blob" and entry.get("mode") == "100644"
                and m.SHA.fullmatch(sha) is not None
                and type(size) is int and 0 < size <= limit,
                "News live file descriptor differs")
        blob = self.get("git/blobs/" + sha)
        m.check(blob.get("sha") == sha and type(blob.get("size")) is int
                and blob["size"] == size and blob.get("encoding") == "base64"
                and isinstance(blob.get("content"), str), "News live blob descriptor differs")
        encoded = "".join(blob["content"].split())
        m.check(len(encoded) == 4 * ((size + 2) // 3), "News live blob encoding size differs")
        raw = base64.b64decode(encoded, validate=True)
        m.check(len(raw) == size and m.blob_sha(raw) == sha, "News live file blob differs")
        return raw


def _load(root: Path) -> dict[str, bytes]:
    m.check(root.is_dir() and not root.is_symlink(), "News live capture directory required")
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        m.check(not path.is_symlink(), "News live capture symlink rejected")
        name = path.relative_to(root).as_posix()
        m.safe_path(name)
        files[name] = path.read_bytes()
    m.check(0 < len(files) <= MAX_FILES
            and sum(map(len, files.values())) <= source.MAX_BUNDLE,
            "News live capture inventory budget")
    return files


def build(files: dict[str, bytes], *, published_at: str) -> tuple[dict, bytes]:
    m.clock(published_at)
    saved = news._decode(files["observations.json"])
    cutoff = saved["projection"]["captured_through"]
    rebuilt = source.rebuild(files, cutoff=cutoff)
    m.check(saved == rebuilt, "News live current window replay differs")
    history = source.replay_history(files, rebuilt)
    hp, cp = history["projection"], rebuilt["projection"]
    m.check(hp["generated_at"] == cp["captured_through"], "News live history/current cutoff differs")
    raw_history = m.json_bytes(history)
    m.check(files.get(HISTORY) == raw_history, "News live saved history bytes differ")
    workflow = cp["workflow"]
    compact_outcomes = [{"source_id": row["source_id"], "status": row["status"],
                         "observations_in_window": row.get("observations_in_window")}
                        for row in cp["source_outcomes"]]
    projection = {
        "version": VERSION,
        "entry_ref": REF,
        "published_at": published_at,
        "code_commit": workflow["code_commit"],
        "source_workflow": source.WORKFLOW,
        "source_run": {
            "run_id": workflow["run_id"],
            "attempt": workflow["attempt"],
            "event": workflow["event"],
            "trigger_run_id": workflow["trigger_run_id"],
        },
        "capture_hash": cp["capture_hash"],
        "captured_from": cp["captured_from"],
        "captured_through": cp["captured_through"],
        "capture_status": cp["status"],
        "source_outcomes": compact_outcomes,
        "history": {
            "read_path": HISTORY,
            "bytes": len(raw_history),
            "sha256": m.sha256(raw_history),
            "git_blob": m.blob_sha(raw_history),
        },
        "rolling": {
            "status": hp["status"],
            "window_start": hp["window_start"],
            "retained_since": hp["retained_since"],
            "coverage": hp["coverage"],
        },
        "complete_news_coverage": False,
        "cache_meaning": CACHE_MEANING,
        "semantics": SEMANTICS,
        **source.AUTHORITY,
    }
    report = {"projection": projection, "projection_hash": canonical_hash(projection)}
    validate(report, history)
    return report, raw_history


def validate(report: dict, history: dict) -> dict:
    m.check(isinstance(report, dict) and set(report) == {"projection", "projection_hash"},
            "News live wrapper differs")
    p = report["projection"]
    keys = {"version", "entry_ref", "published_at", "code_commit", "source_workflow",
            "source_run", "capture_hash", "captured_from", "captured_through", "capture_status",
            "source_outcomes", "history", "rolling", "complete_news_coverage",
            "cache_meaning", "semantics"} | set(source.AUTHORITY)
    m.check(isinstance(p, dict) and set(p) == keys
            and report["projection_hash"] == canonical_hash(p)
            and p["version"] == VERSION and p["entry_ref"] == REF
            and p["source_workflow"] == source.WORKFLOW and p["semantics"] == SEMANTICS
            and p["cache_meaning"] == CACHE_MEANING and p["complete_news_coverage"] is False
            and m.SHA.fullmatch(p["code_commit"]) is not None
            and all(p[k] == v for k, v in source.AUTHORITY.items()),
            "News live contract differs")
    m.clock(p["published_at"]); a, b = m.clock(p["captured_from"]), m.clock(p["captured_through"])
    m.check(a <= b <= m.clock(p["published_at"]), "News live clocks differ")
    run = p["source_run"]
    m.check(set(run) == {"run_id", "attempt", "event", "trigger_run_id"}
            and type(run["run_id"]) is int and run["run_id"] > 0
            and run["attempt"] == 1 and run["event"] in {"schedule", "workflow_dispatch", "workflow_run"},
            "News live source run differs")
    source.workflow_identity({"repository": m.REPOSITORY, "ref": "refs/heads/main",
        "event": run["event"], "code_commit": p["code_commit"], "run_id": run["run_id"],
        "attempt": run["attempt"], "workflow": source.WORKFLOW, "trigger_run_id": run["trigger_run_id"]})
    m.check([x["source_id"] for x in p["source_outcomes"]] == list(source.SOURCES),
            "News live source inventory differs")
    h = p["history"]
    raw = m.json_bytes(history)
    m.check(h == {"read_path": HISTORY, "bytes": len(raw), "sha256": m.sha256(raw),
                  "git_blob": m.blob_sha(raw)}, "News live history descriptor differs")
    hp = source.validate_history(history)["projection"]
    m.check(hp["generated_at"] == p["captured_through"]
            and hp["status"] == p["rolling"]["status"]
            and hp["window_start"] == p["rolling"]["window_start"]
            and hp["retained_since"] == p["rolling"]["retained_since"]
            and hp["coverage"] == p["rolling"]["coverage"],
            "News live rolling projection differs")
    tail = hp["captures"][-1]
    m.check(tail["run_id"] == run["run_id"] and tail["code_commit"] == p["code_commit"]
            and tail["capture_hash"] == p["capture_hash"] and tail["status"] == p["capture_status"],
            "News live tail capture differs")
    return report


def _exact_ref(api, *, fresh=False):
    endpoint = "git/matching-refs/heads/" + REF
    rows = api.fresh_get(endpoint) if fresh else api.get(endpoint)
    m.check(isinstance(rows, list), "News live ref enumeration differs")
    exact = [row for row in rows if row.get("ref") == "refs/heads/" + REF]
    m.check(len(exact) <= 1, "News live ref ambiguous")
    if not exact:
        return None
    sha = exact[0].get("object", {}).get("sha")
    m.check(m.SHA.fullmatch(sha or "") is not None, "News live ref target differs")
    return sha


def publish(api, report: dict, history_raw: bytes) -> str:
    history = news._decode(history_raw)
    validate(report, history)
    manifest_raw = m.json_bytes(report)
    previous = _exact_ref(api)
    if previous:
        prior = news._decode(api.file(MANIFEST, previous))
        m.check(prior.get("projection", {}).get("entry_ref") == REF,
                "News live prior manifest differs")
        m.check(m.clock(prior["projection"]["captured_through"]) < m.clock(report["projection"]["captured_through"]),
                "News live publication would not advance capture time")
    entries = []
    for path, raw in ((MANIFEST, manifest_raw), (HISTORY, history_raw)):
        blob = api.write("git/blobs", {"content": base64.b64encode(raw).decode(), "encoding": "base64"})
        m.check(blob["sha"] == m.blob_sha(raw), "News live published blob differs")
        entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    tree = api.write("git/trees", {"tree": entries})["sha"]
    commit = api.write("git/commits", {"message": "news-live: verified capture "
        + str(report["projection"]["source_run"]["run_id"]), "tree": tree, "parents": []})["sha"]
    m.check(api.file(MANIFEST, commit) == manifest_raw
            and api.file(HISTORY, commit) == history_raw, "News live candidate readback differs")
    current = _exact_ref(api, fresh=True)
    m.check(current == previous, "News live ref changed during publication")
    if previous:
        api.write("git/refs/heads/" + REF, {"sha": commit, "force": True}, "PATCH")
    else:
        api.write("git/refs", {"ref": "refs/heads/" + REF, "sha": commit})
    m.check(_exact_ref(api, fresh=True) == commit, "News live ref readback differs")
    return commit


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        files = _load(args.capture_dir)
        report, history = build(files, published_at=now())
        p = report["projection"]; run = p["source_run"]
        m.check(os.environ["GITHUB_REPOSITORY"] == m.REPOSITORY
                and os.environ["GITHUB_REF"] == "refs/heads/main"
                and os.environ["GITHUB_SHA"] == p["code_commit"]
                and int(os.environ["GITHUB_RUN_ID"]) == run["run_id"]
                and int(os.environ["GITHUB_RUN_ATTEMPT"]) == run["attempt"]
                and os.environ["GITHUB_EVENT_NAME"] == run["event"],
                "News live host identity differs")
        api = NewsLiveGitHubAPI(os.environ["GH_TOKEN"], max_calls=20)
        commit = publish(api, report, history)
        print("NEWS_LIVE_COMMIT=" + commit)
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a") as out:
                out.write("## News live read ref published\n\n")
                out.write(f"Capture {run['run_id']} -> \`{REF}\` commit \`{commit}\`.\n\n")
                out.write("Latest-only read cache; not Research, complete news coverage, or source archive.\n")
        return 0
    except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError,
            RuntimeError, requests.RequestException) as exc:
        print("NEWS_LIVE_PUBLICATION_FAILED: " + type(exc).__name__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
