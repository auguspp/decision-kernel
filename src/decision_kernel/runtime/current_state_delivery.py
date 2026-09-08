"""Bounded GitHub-only collection and atomic publication of a derived reading.

No market/announcement/model calls, no arbitrary URL fetch, no producer dispatch.
Only a dedicated data ref can be written. Source archives are data, never code.
"""
from __future__ import annotations

import argparse
import base64
import copy
import json
import os
import subprocess
import urllib.parse
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests

from . import current_state as model
from .external_research_identity import project_registered_handoffs

MAX_RUNS = 20
MAX_API_CALLS = 180
MAX_SOURCE_FILES = 60
MAX_RETAINED_OUTPUT = 128 * 1024 * 1024
REGISTRY_PATH = "current_state/registry.json"


class GitHubReadError(RuntimeError):
    pass


class GitHubAPI:
    """Narrow repository API client. Errors never echo credentials or response text."""
    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
        self.root = "https://api.github.com/repos/" + model.REPOSITORY + "/"
        self.calls = 0
        self.memo = {}

    def _call(self, method: str, endpoint: str, body=None):
        model.check(not endpoint.startswith("/") and ".." not in endpoint and "://" not in endpoint, "invalid API endpoint")
        if method != "GET":
            model.check((method == "POST" and endpoint in {"git/blobs", "git/trees", "git/commits", "git/refs"})
                        or (method == "PATCH" and endpoint == "git/refs/heads/" + model.READ_REF), "write outside reading Git objects rejected")
            if endpoint == "git/refs":
                model.check(body.get("ref") == "refs/heads/" + model.READ_REF, "wrong publication ref")
        self.calls += 1
        model.check(self.calls <= MAX_API_CALLS, "GitHub request budget exhausted")
        try:
            response = self.session.request(method, self.root + endpoint, json=body,
                                            timeout=45, allow_redirects=False)
        except requests.RequestException as exc:
            raise GitHubReadError("GitHub transport unavailable") from exc
        if response.status_code not in {200, 201, 302}:
            raise GitHubReadError("GitHub HTTP " + str(response.status_code))
        return response

    def get(self, endpoint: str):
        if endpoint not in self.memo:
            response = self._call("GET", endpoint)
            model.check(len(response.content) <= 8 * 1024 * 1024, "GitHub JSON response limit")
            self.memo[endpoint] = response.json()
        return copy.deepcopy(self.memo[endpoint])

    def write(self, endpoint: str, body: dict, method: str = "POST"):
        return self._call(method, endpoint, body).json()

    def file(self, path: str, ref: str) -> bytes:
        model.safe_path(path)
        model.check(model.SHA.fullmatch(ref) is not None, "file reads require exact commit")
        data = self.get("contents/" + urllib.parse.quote(path, safe="/") + "?ref=" + ref)
        model.check(data.get("type") == "file" and data.get("encoding") == "base64", "source is not a bounded text file")
        raw = base64.b64decode(data["content"], validate=False)
        model.check(model.blob_sha(raw) == data["sha"], "GitHub file blob differs")
        return raw

    def archive(self, artifact: dict) -> bytes:
        response = self._call("GET", "actions/artifacts/" + str(int(artifact["id"])) + "/zip")
        model.check(response.status_code == 302, "artifact redirect required")
        target = urllib.parse.urlsplit(response.headers.get("Location", ""))
        model.check(target.scheme == "https" and bool(target.hostname) and not target.username and not target.password
                    and (target.hostname.endswith(".blob.core.windows.net")
                         or target.hostname.endswith(".actions.githubusercontent.com")), "untrusted artifact redirect")
        # Fresh unauthenticated request: never forward repository credentials to storage.
        try:
            with requests.get(target.geturl(), timeout=60, stream=True, allow_redirects=False) as downloaded:
                model.check(downloaded.status_code == 200, "artifact download unavailable")
                chunks, count = [], 0
                for chunk in downloaded.iter_content(1024 * 1024):
                    count += len(chunk)
                    model.check(count <= model.MAX_ARCHIVE, "archive download limit")
                    chunks.append(chunk)
                return b"".join(chunks)
        except requests.RequestException as exc:
            raise GitHubReadError("artifact transport unavailable") from exc


def git_file(root: Path, code_commit: str, path: str) -> bytes:
    model.safe_path(path)
    model.check(model.SHA.fullmatch(code_commit) is not None, "checkout must be pinned")
    try:
        result = subprocess.run(["git", "show", code_commit + ":" + path], cwd=root,
                                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout
    except subprocess.CalledProcessError as exc:
        raise ValueError("pinned repository file unavailable") from exc


class Collector:
    def __init__(self, api, code_commit: str, root: Path, previous: dict | None = None,
                 previous_commit: str | None = None, now=None):
        model.check(model.SHA.fullmatch(code_commit) is not None, "exact code commit required")
        self.api, self.code_commit, self.root = api, code_commit, root
        self.previous, self.previous_commit = previous, previous_commit
        self.now = now or (lambda: datetime.now(timezone.utc).isoformat())
        self.files = {}
        self.sources = {}
        self.archive_cache = {}

    def retain(self, path: str, raw: bytes) -> dict:
        model.safe_path(path)
        model.check(not path.startswith(".github/"), "reading ref cannot contain executable workflow")
        if path in self.files:
            model.check(self.files[path] == raw, "conflicting retained bytes")
        self.files[path] = raw
        model.check(sum(len(v) for v in self.files.values()) <= MAX_RETAINED_OUTPUT, "reading retention batch limit")
        return {"read_path": path, "sha256": model.sha256(raw), "git_blob": model.blob_sha(raw), "bytes": len(raw),
                "read_ref_rule": "USE_THE_SAME_PINNED_READING_COMMIT"}

    def source(self, spec: dict) -> tuple[bytes, dict]:
        path, ref = model.safe_path(spec["path"]), spec.get("ref", self.code_commit)
        key = (path, ref)
        if key not in self.sources:
            model.check(len(self.sources) < MAX_SOURCE_FILES, "source registry bound")
            raw = git_file(self.root, ref, path) if ref == self.code_commit else self.api.file(path, ref)
            stored = self.retain("sources/git/" + model.blob_sha(raw) + "/" + Path(path).name, raw)
            self.sources[key] = (raw, {"repository": model.REPOSITORY, "ref": ref, "path": path,
                                       "git_blob": model.blob_sha(raw), **stored})
        raw, reference = self.sources[key]
        if spec.get("git_blob"):
            model.check(reference["git_blob"] == spec["git_blob"], "registered frozen blob changed")
        if spec.get("contains"):
            model.check(all(s in raw.decode() for s in spec["contains"]), "registered source purpose evidence missing")
        return raw, reference

    def archive(self, artifact: dict, run: dict) -> tuple[dict, dict]:
        key = artifact["id"]
        model.check(not artifact.get("expired", True), "latest artifact expired")
        if key in self.archive_cache:
            _, prior = self.archive_cache[key]
            origin = artifact.get("workflow_run", {})
            model.check(origin.get("id") == run["id"] == prior["origin_run"]["id"]
                        and origin.get("head_sha") == run["head_sha"] == prior["origin_run"]["head_sha"]
                        and artifact.get("digest") == "sha256:" + prior["sha256"]
                        and artifact.get("size_in_bytes") == prior["bytes"], "cached archive identity changed")
        if key not in self.archive_cache:
            # Reuse a previously retained exact archive only while current remote
            # metadata still makes that same artifact admissible. Never restore from it.
            cached = []
            for old_lane in (self.previous or {}).get("lanes", {}).values():
                old = old_lane.get("last_qualified_result") or {}
                cached.extend(old[k] for k in ("archive", "state_archive") if k in old)
            match = next((r for r in cached if r.get("artifact_id") == key
                          and "sha256:" + r["sha256"] == artifact.get("digest")), None)
            if match:
                stored = self.api.get("git/blobs/" + match["git_blob"])
                raw = base64.b64decode(stored["content"])
                model.check(model.blob_sha(raw) == match["git_blob"], "cached read archive corrupt")
            else:
                raw = self.api.archive(artifact)
            files = model.unpack_archive(raw, artifact, run)
            stored = self.retain("sources/artifacts/" + model.sha256(raw) + ".zip", raw)
            reference = {**stored, "artifact_id": key, "artifact_name": artifact["name"],
                         "expires_at": artifact.get("expires_at"), "origin_run": model.concise_run(run),
                         "artifact_url": f"https://github.com/{model.REPOSITORY}/actions/runs/{run['id']}/artifacts/{key}",
                         "meaning": "EXACT_ARCHIVE_READ_COPY_NOT_PRODUCTION_RESTORE"}
            self.archive_cache[key] = (files, reference)
        return self.archive_cache[key]

    def artifacts(self, run: dict) -> list[dict]:
        data = self.api.get(f"actions/runs/{run['id']}/artifacts?per_page=100")
        model.check(data["total_count"] <= len(data["artifacts"]), "artifact enumeration incomplete")
        return data["artifacts"]

    def runs(self, lane: str) -> tuple[list[dict], bool]:
        filename = Path(model.WORKFLOWS[lane]).name
        data = self.api.get(f"actions/workflows/{filename}/runs?branch=main&per_page={MAX_RUNS}")
        candidates = data["workflow_runs"]
        model.check(len(candidates) <= MAX_RUNS, "unexpected run query bound")
        model.check(bool(candidates) or data["total_count"] == 0, "empty run page with missing results")
        # Workflow-specific newest page establishes the newest attempt, not all history.
        if lane != "stock":
            return candidates, True
        stock, complete = [], True
        for run in candidates:
            jobs = self.api.get(f"actions/runs/{run['id']}/jobs?per_page=100")
            model.check(jobs["total_count"] <= len(jobs["jobs"]), "stock job enumeration incomplete")
            relevant = [j for j in jobs["jobs"] if j["name"] == "stock-reading"
                        and j.get("conclusion") != "skipped"]
            if relevant:
                stock.append(run)
            elif (run.get("status") != "completed" or
                  (not any(j["name"] == "stock-reading" for j in jobs["jobs"]) and run.get("conclusion") != "success")):
                # Purpose cannot be inferred before job metadata exists, or if
                # a failed run never exposed enough metadata to identify its purpose.
                complete = False
        return stock, complete

    def saved_product(self, lane: str, run: dict) -> dict:
        model.run_identity(run, lane, success=True)
        artifacts = self.artifacts(run)
        name = (f"sector-radar-run-{run['id']}" if lane == "sector" else
                f"stock-reading-{run['id']}-1" if lane == "stock" else "decision-inbox")
        files, archive_ref = self.archive(model.select_artifact(artifacts, name), run)
        prefix = f"details/{lane}/{run['id']}/"
        run_reference = self.retain(prefix + "run.json", model.json_bytes(run))
        if lane == "sector":
            state, state_ref = self.archive(model.select_artifact(artifacts, "sector-radar-state-bundle"), run)
            result = model.validate_sector(run, files, state)
            details = {n: self.retain(prefix + n, files[n]) for n in (
                "context/context.json", "operations.json", "publication-verification.json")}
            # Original summary is explicitly original; current renderer not backdated.
            for name in ("summary.md", "context/index.html", "result.json"):
                if name in files:
                    details[name] = self.retain(prefix + name, files[name])
            result["state_archive"] = state_ref
        elif lane == "stock":
            result = model.validate_stock(run, files)
            details = {n: self.retain(prefix + n, files[n]) for n in (
                "reading/stock-reading.json", "reading/index.html", "verification.json", "market-binding.json")}
        else:
            model.check("summary.md" in files and "index.html" in files, "Inbox reading missing")
            # The existing CLI saves HTML/Markdown, not a typed DecisionSpineResult.
            # Preserve delivery only; do NOT parse prose into current Odds/Decision authority.
            result = {"status": "SAVED_INBOX_DELIVERY_ONLY", "numeric_result_validation": "NOT_AVAILABLE_IN_EXISTING_ARTIFACT",
                      "market_session": None, "odds_recomputed": False,
                      "limitation": "Markdown/HTML retained as untrusted historical output; no inferred quiet or accepted probability"}
            details = {n: self.retain(prefix + n, files[n]) for n in ("summary.md", "index.html")}
        return {**result, "run": model.concise_run(run), "archive": archive_ref, "details": details,
                "source_checked_at": self.now(), "run_metadata": run_reference}

    def lane(self, lane: str) -> dict:
        latest, qualified, failure, query_complete = None, None, None, False
        try:
            runs, query_complete = self.runs(lane)
            latest, successful = model.select_runs(runs, lane)
            if latest:
                model.run_identity(latest, lane)
                if lane == "sector" and latest.get("conclusion") == "failure":
                    try:
                        bad = model.select_artifact(self.artifacts(latest), f"sector-radar-run-{latest['id']}")
                        failed_files, failure_source = self.archive(bad, latest)
                        operation = json.loads(failed_files["operations.json"])
                        model.sealed(operation, "operations_hash")
                        model.check(operation["run_id"] == latest["id"] and operation["commit_sha"] == latest["head_sha"], "failure identity differs")
                        latest = dict(latest, operation={k: operation.get(k) for k in (
                            "status", "error_type", "error_message", "latest_cached_session",
                            "latest_completed_session", "direct_next_session")})
                        latest["operation"]["source"] = failure_source
                    except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError, zipfile.BadZipFile):
                        latest = dict(latest, operation={"status": "FAILURE_DETAIL_UNAVAILABLE_NOT_QUIET"})
            if successful:
                # Exactly one chosen success. A rejected archive never triggers older search.
                qualified = self.saved_product(lane, successful)
            else:
                failure = "NO_SUCCESS_IN_BOUNDED_QUERY"
        except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
            failure = "INPUT_UNAVAILABLE_OR_REJECTED:" + type(exc).__name__ + ":" + str(exc)[:180]
        previous = (self.previous or {}).get("lanes", {}).get(lane)
        result = model.lane_reading(latest=latest, qualified=qualified, failure=failure,
                                   checked_at=self.now(), query_complete=query_complete, previous=previous)
        if qualified is None and result["last_qualified_result"] is not None:
            result["previous_read_commit"] = self.previous_commit
        result["query_scope"] = f"newest {MAX_RUNS} runs of exact workflow on main; not an all-history audit"
        return result

    def research(self, registry: dict) -> dict:
        records, packages, gaps, entries = [], [], [], []
        configuration = None
        try:
            raw, configuration = self.source({"path": model.WORKFLOWS["inbox"]})
            package_paths = model.configured_paths(raw.decode(), "decision_packages")
            handoff_paths = model.configured_paths(raw.decode(), "research_attention_handoffs")
            for path in package_paths:
                try:
                    data, source = self.source({"path": path})
                    value = json.loads(data)
                    model.check(isinstance(value, dict), "production package must be an object")
                    if "deep_research" in value and "discovery" in value:
                        from decision_kernel.deep_research import DeepResearchPackage
                        DeepResearchPackage.model_validate(value)
                        kind = "DeepResearchPackage"
                    else:
                        from decision_kernel.research_commit import ResearchCommitPackage
                        ResearchCommitPackage.model_validate(value)
                        kind = "ResearchCommitPackage"
                    packages.append({"source": source, "label": value.get("label", path), "schema": kind,
                        "use": "CURRENT_PRODUCTION_CONFIG_INPUT_NOT_NEW_ODDS_OR_HUMAN_ACCEPTANCE"})
                except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError) as exc:
                    gaps.append({"path": path, "status": "PRODUCTION_INPUT_REJECTED_NOT_REMOVED", "error_type": type(exc).__name__})
            history = copy.deepcopy(registry["historical_handoffs"])
            for path in handoff_paths:
                entry = {"source": {"path": path}, "registered_current": True}
                try:
                    current, _ = self.source(entry["source"])
                    matches = [h for h in history if h["source"]["path"] == path and
                               (h["source"].get("git_blob") == model.blob_sha(current) or
                                h.get("resolved_handoff_sha256") == model.sha256(current))]
                    if len(matches) == 1:
                        entry = matches[0]
                        history.remove(entry)
                        entry["registered_current"] = True
                except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError):
                    pass  # The original parser below records this input's failure.
                entries.append(entry)
            entries.extend(history)  # Never collapse multiple versions by ticker/path.
        except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError) as exc:
            gaps.append({"status": "PRODUCTION_REGISTRATION_UNAVAILABLE", "error_type": type(exc).__name__})
            # Independent explicitly registered handoffs remain readable.
        entries.extend(registry.get("additional_registered_handoffs", []))
        for record in registry["references"]:
            try:
                raw, source = self.source(record["source"])
                records.append({"id": record["id"], "case": record["case"], "use": record["use"],
                                "purpose_note": record["purpose_note"], "source": source,
                                "qualification": "EXPLICIT_PURPOSE_REFERENCE_NOT_AUTOMATIC_SUPERSESSION"})
            except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError) as exc:
                gaps.append({"id": record["id"], "status": "RESEARCH_REFERENCE_REJECTED", "error_type": type(exc).__name__})
        return {"production_configuration": configuration, "production_inputs": packages,
                "records": records, "handoffs": project_registered_handoffs(entries, self.source), "gaps": gaps,
                "confirmed_actions": [r for r in records if r["use"] == "CONFIRMED_ACTION_CHECKPOINT"],
                "confirmed_action_scope": "EXPLICIT_REGISTRY_ONLY_NOT_PROOF_NO_TRADES_OCCURRED",
                "scope": "EXPLICIT_CONFIG_AND_REGISTERED_LINEAGE_NOT_EXHAUSTIVE_RESEARCH_COVERAGE"}

    def collect(self, refresh: dict) -> dict:
        started = self.now()
        raw, registry_ref = self.source({"path": REGISTRY_PATH})
        registry = json.loads(raw)
        model.check(registry["schema_version"] == 1, "registry unsupported")
        lanes = {name: self.lane(name) for name in model.WORKFLOWS}
        research = self.research(registry)
        research["registry"] = registry_ref
        capabilities = []
        for item in registry["capability_gaps"]:
            try:
                _, reference = self.source(item["source"])
                capabilities.append({"id": item["id"], "status": item["status"], "source": reference})
            except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError):
                capabilities.append({"id": item["id"], "status": "ACCEPTANCE_SOURCE_UNAVAILABLE"})
        payload = model.assemble(code_commit=self.code_commit, checked_at=self.now(), check_started_at=started,
                                 lanes=lanes, research=research, capabilities=capabilities, refresh_identity=refresh)
        self.retain("current-state.json", model.json_bytes(payload))
        self.retain("README.md", model.render_summary(payload).encode())
        return payload


def publish(api, files: dict[str, bytes], previous_commit: str | None, code_commit: str, reading_hash: str) -> str:
    """Atomic, fast-forward-only publication; a concurrent writer wins or this fails."""
    tree_entries = []
    for path, raw in sorted(files.items()):
        model.safe_path(path)
        model.check(not path.startswith(".github/"), "executable content on read ref rejected")
        blob = api.write("git/blobs", {"content": base64.b64encode(raw).decode(), "encoding": "base64"})
        model.check(blob["sha"] == model.blob_sha(raw), "published blob read identity differs")
        tree_entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    body = {"tree": tree_entries}
    if previous_commit:
        body["base_tree"] = api.get("git/commits/" + previous_commit)["tree"]["sha"]
    tree = api.write("git/trees", body)["sha"]
    commit = api.write("git/commits", {"message": "read-model: saved result snapshot " + reading_hash,
        "tree": tree, "parents": [previous_commit] if previous_commit else []})["sha"]
    # Validate the immutable candidate BEFORE advancing the readable pointer.
    # Failed readback leaves the previous ref unchanged. An uncertain ref-write
    # response is never retried: inspect its actual state separately.
    model.check(api.file("current-state.json", commit) == files["current-state.json"], "publication readback mismatch")
    if previous_commit:
        api.write("git/refs/heads/" + model.READ_REF, {"sha": commit, "force": False}, "PATCH")
    else:
        api.write("git/refs", {"ref": "refs/heads/" + model.READ_REF, "sha": commit})
    return commit


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Read saved GitHub results; never run market or Research producers")
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args(argv)
    model.check(model.SHA.fullmatch(args.code_commit) is not None, "code commit required")
    api = GitHubAPI(os.environ["GH_TOKEN"])
    prior_commit = None
    previous = None
    try:
        refs = api.get("git/matching-refs/heads/" + model.READ_REF)
        exact = [r for r in refs if r["ref"] == "refs/heads/" + model.READ_REF]
        model.check(len(exact) <= 1, "ambiguous reading ref")
        if exact:
            prior_commit = exact[0]["object"]["sha"]
            previous = json.loads(api.file("current-state.json", prior_commit))
            model.validate_read_package(previous)
        collector = Collector(api, args.code_commit, Path.cwd(), previous, prior_commit)
        refresh = {"workflow": ".github/workflows/current-state-read-entry.yml",
                   "run_id": os.environ.get("GITHUB_RUN_ID"), "attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
                   "event": os.environ.get("GITHUB_EVENT_NAME"), "trigger_run_id": os.environ.get("TRIGGER_RUN_ID"),
                   "publication_status": "BLOB_READBACK_REQUIRED_NOT_UPSTREAM_PRODUCTION_ACCEPTANCE"}
        payload = collector.collect(refresh)
        args.output.mkdir(parents=True, exist_ok=False)
        for path, raw in collector.files.items():
            target = args.output / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        if args.publish:
            commit = publish(api, collector.files, prior_commit, args.code_commit, payload["reading_hash"])
            print("READ_ENTRY_COMMIT=" + commit)
            summary = os.environ.get("GITHUB_STEP_SUMMARY")
            if summary:
                with open(summary, "a") as out:
                    out.write("## Current-state read entry published\n\n")
                    out.write(f"`{model.REPOSITORY}` / `{model.READ_REF}` / commit `{commit}` / `current-state.json`.\n\n")
                    out.write("This is a read-only delivery, not market/Research execution or natural Sector acceptance.\n")
        return 0
    except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError, requests.RequestException) as exc:
        print("READ_ENTRY_PUBLICATION_FAILED: " + type(exc).__name__)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
