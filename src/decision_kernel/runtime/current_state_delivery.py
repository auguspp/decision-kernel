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
MAX_RESEARCH_WORK_ITEMS = 10  # Seven retained parents plus two explicitly authorized children.
RESEARCH_WORK_API_RESERVE = 12
REGISTRY_PATH = "current_state/registry.json"


class GitHubReadError(RuntimeError):
    pass


def research_work_diagnostic(exc: Exception, *, api_calls, source_count: int,
                             retained_file_count: int) -> dict:
    """Report only our static rejection labels, never exception/source contents."""
    labels = {
        "research work API accounting unavailable": "API_ACCOUNTING_UNAVAILABLE",
        "research work API reserve would consume base publication budget": "BASE_PUBLICATION_RESERVE",
        "research work item bound exceeded": "WORK_ITEM_BOUND",
        "research work read would exceed source-file budget": "SOURCE_FILE_BUDGET",
        "research work would exhaust reading retention bound": "RETENTION_BYTE_BUDGET",
        "research work read would exhaust publication API reserve": "WORK_PUBLICATION_RESERVE",
        "research work tree incomplete": "INCOMPLETE_WORK_TREE",
        "research work reserved packet unavailable": "RESERVED_PACKET_UNAVAILABLE",
        "research work item contains both candidate and pre-execution failure": "CANDIDATE_FAILURE_CONFLICT",
        "research work blob differs": "WORK_BLOB_MISMATCH",
        "research work failure packet binding differs": "FAILURE_PACKET_MISMATCH",
        "saved Funnel differs from original candidate revalidation": "SAVED_FUNNEL_MISMATCH",
    }
    # A validator or transport exception may contain untrusted text or secrets.
    # Do not stringify it, publish a URL/body, or guess a cause for unknown errors.
    message = exc.args[0] if (type(exc) is ValueError and len(exc.args) == 1
                             and type(exc.args[0]) is str) else None
    return {
        "code": labels.get(message, "UNCLASSIFIED_READ_REJECTION"),
        "api_calls_after_attempt": api_calls if type(api_calls) is int and api_calls >= 0 else None,
        "source_count_after_rollback": source_count,
        "retained_file_count_after_rollback": retained_file_count,
        "meaning": "DIAGNOSTIC_ONLY_NOT_RECOVERY_OR_RESEARCH_ACCEPTANCE",
    }


class GitHubAPI:
    """Narrow repository API client. Errors never echo credentials or response text."""
    def __init__(self, token: str, *, max_calls: int = MAX_API_CALLS):
        model.check(type(max_calls) is int and 1 <= max_calls <= 1024, "invalid repository request bound")
        self.max_calls = max_calls
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
        model.check(self.calls <= self.max_calls, "GitHub request budget exhausted")
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
        self.inbox_job_checks = {}
        self.inbox_job_gaps = []

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
            # Match select_runs' existing production-trigger scope before checking
            # purpose. Historical push-only trials cannot make production unknown.
            if run.get("event") not in {"schedule", "workflow_dispatch"}:
                continue
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

    def failed_run_inbox_check(self, run: dict) -> dict:
        """Qualify only the Inbox job of a completed failed attempt, never its Odds.

        GitHub's attempt-specific endpoint avoids borrowing jobs from a rerun.
        Existing whole-run success qualification is unchanged. This proof cannot
        turn the parent workflow or a failed disclosure scan green.
        """
        model.run_identity(run, "inbox")
        model.check(run.get("status") == "completed" and run.get("conclusion") == "failure",
                    "Inbox job exception requires completed failed workflow")
        if run["id"] in self.inbox_job_checks:
            proof = self.inbox_job_checks[run["id"]]
            model.check(proof["head_sha"] == run["head_sha"], "cached Inbox job commit differs")
            return proof
        data = self.api.get(f"actions/runs/{run['id']}/attempts/1/jobs?per_page=100")
        jobs = data["jobs"]
        model.check(isinstance(jobs, list) and 0 < len(jobs) <= 100
                    and data["total_count"] == len(jobs), "Inbox job enumeration incomplete")
        ids = [job["id"] for job in jobs]
        model.check(all(type(i) is int and i > 0 for i in ids) and len(set(ids)) == len(ids),
                    "Inbox job identities invalid or duplicated")
        for job in jobs:
            model.check(job.get("run_id") == run["id"] and job.get("head_sha") == run["head_sha"],
                        "Inbox job belongs to another run or commit")
            model.check(job.get("status") == "completed" and bool(job.get("conclusion")),
                        "completed workflow has unfinished job metadata")
        inbox = [job for job in jobs if job.get("name") == "inbox"]
        disclosures = [job for job in jobs if job.get("name") == "disclosures"]
        model.check(len(inbox) == len(disclosures) == 1, "Inbox or disclosure job missing or ambiguous")
        job = inbox[0]
        succeeded = job["conclusion"] == "success"
        if succeeded:
            model.check(model.clock(run["created_at"]) <= model.clock(job["started_at"])
                        <= model.clock(job["completed_at"]) <= model.clock(run["updated_at"]),
                        "Inbox job clocks outside workflow")
            for name in ("Build Attention Inbox", "Upload mobile HTML snapshot"):
                steps = [step for step in job.get("steps", []) if step.get("name") == name]
                model.check(len(steps) == 1 and steps[0].get("status") == "completed"
                            and steps[0].get("conclusion") == "success", "Inbox delivery step not successful")
        source = self.retain(f"details/inbox/{run['id']}/attempt-1-jobs.json", model.json_bytes(data))
        proof = {"run_id": run["id"], "run_attempt": 1, "head_sha": run["head_sha"],
                 "workflow_conclusion": run["conclusion"], "inbox_job_id": job["id"],
                 "inbox_conclusion": job["conclusion"], "delivery_job_succeeded": succeeded,
                 "sibling_jobs": [{k: item.get(k) for k in ("id", "name", "status", "conclusion")}
                                  for item in jobs if item["id"] != job["id"]],
                 "source": source, "meaning": "SAVED_DELIVERY_JOB_ONLY_NOT_REVALIDATED_ODDS"}
        self.inbox_job_checks[run["id"]] = proof
        return proof

    def select_inbox_delivery(self, runs: list[dict]) -> dict | None:
        # The bounded list is the same list used for latest_attempt. Stop at the
        # first qualified delivery; artifact rejection never searches farther.
        model.check(len(runs) <= MAX_RUNS, "Inbox run query bound")
        eligible = [run for run in runs if model.select_runs([run], "inbox")[0] is not None]
        for run in sorted(eligible, key=lambda item: (model.clock(item["created_at"]), item["id"]), reverse=True):
            model.run_identity(run, "inbox")
            if run.get("status") != "completed":
                continue
            if run.get("conclusion") == "success":
                return run  # Preserve the original success path, not a new schema.
            if run.get("conclusion") != "failure":
                continue  # Cancelled/skipped/unknown runs are not new deliveries.
            try:
                if self.failed_run_inbox_check(run)["delivery_job_succeeded"]:
                    return run
            except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError) as exc:
                self.inbox_job_gaps.append({"run_id": run["id"], "status": "INBOX_JOB_CHECK_INCOMPLETE",
                                           "error_type": type(exc).__name__})
                # An older independently successful result may remain historical;
                # missing job metadata is never converted into today's success.
        return None

    def saved_product(self, lane: str, run: dict) -> dict:
        inbox_job = None
        if lane == "inbox" and run.get("conclusion") == "failure":
            inbox_job = self.failed_run_inbox_check(run)
            model.check(inbox_job["delivery_job_succeeded"], "Inbox delivery job failed")
        else:
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
            for name in ("summary.md", "context/index.html", "result.json", "stock-reference.json"):
                if name in files:
                    details[name] = self.retain(prefix + name, files[name])
            result["state_archive"] = state_ref
        elif lane == "stock":
            result = model.validate_stock(run, files)
            names = ["reading/stock-reading.json", "reading/index.html", "verification.json", "market-binding.json"]
            if "market-context-binding.json" in files:
                names += ["market-context-binding.json", "reading/inputs/sector-result.json"]
            details = {n: self.retain(prefix + n, files[n]) for n in names}
        else:
            model.check("summary.md" in files and "index.html" in files, "Inbox reading missing")
            # The existing CLI saves HTML/Markdown, not a typed DecisionSpineResult.
            # Preserve delivery only; do NOT parse prose into current Odds/Decision authority.
            result = {"status": "SAVED_INBOX_DELIVERY_ONLY", "numeric_result_validation": "NOT_AVAILABLE_IN_EXISTING_ARTIFACT",
                      "market_session": None, "odds_recomputed": False,
                      "limitation": "Markdown/HTML retained as untrusted historical output; no inferred quiet or accepted probability"}
            details = {n: self.retain(prefix + n, files[n]) for n in ("summary.md", "index.html")}
            if inbox_job is not None:
                result["job_qualification"] = inbox_job
        return {**result, "run": model.concise_run(run), "archive": archive_ref, "details": details,
                "source_checked_at": self.now(), "run_metadata": run_reference}

    def sector_result_after_validation(self, runs: list[dict], checked: dict) -> tuple[dict, dict | None]:
        """A verified same-session no-op must not erase its result-bearing predecessor.

        This is reading selection, never restore or a new event. Every inspected
        archive still passes saved_product; corruption stops, not older fallback.
        """
        noop = "VALIDATED_ALREADY_CURRENT_NO_PROSPECTIVE_EVENT"
        if checked.get("status") != noop:
            return checked, None
        identity = ("market_session", "market_state_hash", "event_ledger_hash")
        expected = tuple(checked[key] for key in identity)
        boundary = (model.clock(checked["run"]["created_at"]), checked["run"]["id"])
        eligible = [r for r in runs if model.select_runs([r], "sector")[1] is not None]
        model.check(len(eligible) <= MAX_RUNS, "Sector delivery scan bound")
        for run in sorted(eligible, key=lambda r: (model.clock(r["created_at"]), r["id"]), reverse=True):
            if (model.clock(run["created_at"]), run["id"]) >= boundary:
                continue
            prior = self.saved_product("sector", run)
            if prior["market_session"] != checked["market_session"]:
                break  # Never carry another market day as this day's changes.
            model.check(tuple(prior[key] for key in identity) == expected,
                        "same-session Sector result/state continuity differs")
            if prior["status"] == noop:
                continue
            model.check("result.json" in prior["details"] and "summary.md" in prior["details"],
                        "result-bearing Sector delivery is incomplete")
            return prior, checked
        return checked, checked

    def lane(self, lane: str) -> dict:
        latest, qualified, failure, query_complete = None, None, None, False
        state_validation = None
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
            if lane == "inbox":
                successful = self.select_inbox_delivery(runs)
            if successful:
                # Exactly one chosen success. A rejected archive never triggers older search.
                qualified = self.saved_product(lane, successful)
                if lane == "sector":
                    qualified, state_validation = self.sector_result_after_validation(runs, qualified)
            else:
                failure = "NO_SUCCESS_IN_BOUNDED_QUERY"
        except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
            failure = "INPUT_UNAVAILABLE_OR_REJECTED:" + type(exc).__name__ + ":" + str(exc)[:180]
        previous = (self.previous or {}).get("lanes", {}).get(lane)
        result = model.lane_reading(latest=latest, qualified=qualified, failure=failure,
                                   checked_at=self.now(), query_complete=query_complete, previous=previous)
        if qualified is None and result["last_qualified_result"] is not None:
            result["previous_read_commit"] = self.previous_commit
        if lane == "inbox":
            if latest and latest["id"] in self.inbox_job_checks:
                result["latest_job_check"] = self.inbox_job_checks[latest["id"]]
            if self.inbox_job_gaps:
                result["job_check_gaps"] = self.inbox_job_gaps
                result["gaps"].append("INBOX_JOB_CHECK_INCOMPLETE_NOT_CURRENT_SUCCESS")
            if qualified and qualified.get("job_qualification"):
                result["gaps"].append("INBOX_DELIVERY_PRESERVED_WORKFLOW_FAILURE_NOT_HIDDEN")
                if latest and latest["id"] == qualified["run"]["id"]:
                    result["gaps"] = [gap for gap in result["gaps"]
                                      if gap != "LATEST_ATTEMPT_IS_NOT_A_NEW_QUALIFIED_DELIVERY"]
        if state_validation is not None:
            result["latest_state_validation"] = state_validation
            result["delivery_selection"] = "SAME_SESSION_RESULT_PRESERVED_NOT_NEW_EVENT"
            if qualified["run"]["id"] == state_validation["run"]["id"]:
                result["gaps"].append("SAME_SESSION_RESULT_NOT_FOUND_IN_BOUNDED_QUERY")
        result["query_scope"] = f"newest {MAX_RUNS} runs of exact workflow on main; not an all-history audit"
        return result

    def research_work(self, config: dict) -> dict:
        """Stage optional reading in memory; rejected work cannot impair base delivery."""
        before_files, before_sources = dict(self.files), dict(self.sources)
        try:
            return self._research_work(config)
        except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError):
            # Only discard this invocation's unaccepted local projection. No Git
            # write, history reset, source retry or API-call counter rollback.
            self.files, self.sources = before_files, before_sources
            raise

    def _research_work(self, config: dict) -> dict:
        """Read retained disclosure Research work without promoting it to current attention.

        The work ref is data-only. Existing packet/input/candidate validators establish
        identity and Funnel shape only; this reader does not grant semantic acceptance,
        Human attention, continuation authority or investment authority.
        """
        from decision_kernel.research_workflow_v1 import ResearchFunnelResult
        from . import incremental_disclosure as work
        from .external_research_execution import (
            ExternalResearchInputPacket, ExternalResearchValidationResult,
        )
        from .external_research_identity import _json
        from .incremental_disclosure_intake import work_inventory

        expected = {"ref", "prefix", "mode", "max_items"}
        model.check(isinstance(config, dict) and set(config) == expected,
                    "research work read config differs")
        model.check(config["ref"] == work.WORK_REF and config["prefix"] == work.WORK_PREFIX,
                    "research work read points outside approved work ref")
        model.check(config["mode"] == "RETAINED_DISCLOSURE_CANDIDATE_READ_ONLY",
                    "research work read mode differs")
        model.check(type(config["max_items"]) is int and 1 <= config["max_items"] <= MAX_RESEARCH_WORK_ITEMS,
                    "research work read item bound invalid")

        # publish() writes every retained blob, two entry files, then at most
        # five Git operations (prior commit, tree, commit, readback, ref). Reject
        # even metadata reads when they would steal the base publication budget.
        entry_paths = {"current-state.json", "README.md"}
        used = getattr(self.api, "calls", None)
        model.check(type(used) is int and used >= 0, "research work API accounting unavailable")
        model.check(used + 2 + len(set(self.files) | entry_paths) + 5 <= MAX_API_CALLS,
                    "research work API reserve would consume base publication budget")
        ref = self.api.get("git/ref/heads/" + work.WORK_REF)["object"]
        model.check(ref.get("type") == "commit" and model.SHA.fullmatch(ref.get("sha", "")) is not None,
                    "research work ref is not a pinned commit")
        work_commit = ref["sha"]
        tree = self.api.get("git/trees/" + work_commit + "?recursive=1")
        model.check(tree.get("truncated") is False and isinstance(tree.get("tree"), list),
                    "research work tree incomplete")

        prefix = work.WORK_PREFIX
        rows = {row["path"]: row for row in tree["tree"] if row.get("type") == "blob"}
        keys: dict[tuple[str, str], set[str]] = {}
        for path in rows:
            if not path.startswith(prefix):
                continue
            key, base, name = work.split_work_path(path)
            keys.setdefault((key, base), set()).add(name)
        model.check(len(keys) <= config["max_items"], "research work item bound exceeded")

        needed = set()
        for (key, base), names in keys.items():
            needed.add(work.request_path(key))
            if base != work.request_path(key).removesuffix("packet.json"):
                needed.add(work.request_path(key).replace("packet.json", "failure.json"))
            for name in ("input.json", "candidate.json", "funnel.json", "failure.json"):
                if name in names:
                    needed.add(base + name)
        model.check(needed.issubset(rows), "research work reserved packet unavailable")
        new_sources = {(path, work_commit) for path in needed} - set(self.sources)
        model.check(len(self.sources) + len(new_sources) <= MAX_SOURCE_FILES,
                    "research work read would exceed source-file budget")
        new_files = {}
        for path in needed:
            row = rows[path]
            size, blob = row.get("size"), row.get("sha", "")
            model.check(row.get("mode") == "100644" and type(size) is int
                        and 0 <= size <= model.MAX_ARCHIVE and model.SHA.fullmatch(blob),
                        "research work source metadata invalid")
            read_path = "sources/git/" + blob + "/" + Path(path).name
            if read_path in new_files:
                model.check(new_files[read_path] == size, "research work source metadata conflicts")
            new_files[read_path] = size
        extra_bytes = sum(size for path, size in new_files.items() if path not in self.files)
        model.check(sum(map(len, self.files.values())) + extra_bytes <= MAX_RETAINED_OUTPUT,
                    "research work would exhaust reading retention bound")
        # work_inventory's tree request is memoized by GitHubAPI; reserve one
        # extra request anyway. Include all source reads and all new blob writes.
        remaining_reads = len(needed) + 1
        publication_calls = len(set(self.files) | set(new_files) | entry_paths) + 5
        model.check(self.api.calls + remaining_reads + max(RESEARCH_WORK_API_RESERVE, publication_calls)
                    <= MAX_API_CALLS, "research work read would exhaust publication API reserve")

        _, work_files = work_inventory(self.api, work_commit)

        def retained(path: str, raw: bytes) -> dict:
            row = rows[path]
            model.check(row.get("mode") == "100644" and row.get("size") == len(raw)
                        and row.get("sha") == model.blob_sha(raw), "research work blob differs")
            source_key = (path, work_commit)
            if source_key in self.sources:
                model.check(self.sources[source_key][0] == raw, "research work source cache differs")
                return self.sources[source_key][1]
            model.check(len(self.sources) < MAX_SOURCE_FILES, "source registry bound")
            stored = self.retain("sources/git/" + row["sha"] + "/" + Path(path).name, raw)
            reference = {"repository": model.REPOSITORY, "ref": work_commit, "path": path,
                         "git_blob": row["sha"], **stored}
            self.sources[source_key] = (raw, reference)
            return reference

        def fetched(path: str) -> tuple[bytes, dict]:
            raw = self.api.file(path, work_commit)
            return raw, retained(path, raw)

        items = []
        for key, base in sorted(keys):
            names = keys[key, base]
            is_child = base != work.request_path(key).removesuffix("packet.json")
            comment_id = int(base.rstrip("/").rsplit("/", 1)[1]) if is_child else None
            lineage = {} if not is_child else {"work_kind": "HUMAN_SAME_SOURCE_READING_CONTINUATION",
                "permission_comment_id": comment_id, "parent_assessment_input_hash": key,
                "execution_id": f"saved-disclosure-{key}-reading-{comment_id}",
                "candidate_output_prefix": base, "new_disclosure": False}
            if is_child:
                model.check("failure.json" in keys.get((key, work.request_path(key).removesuffix("packet.json")), set()),
                            "source-reading child lacks retained parent failure")
            packet_path = work.request_path(key)
            model.check(packet_path in work_files and work_files[packet_path],
                        "research work reserved packet unavailable")
            packet_raw = work_files[packet_path]
            packet_source = retained(packet_path, packet_raw)
            has_candidate = "candidate.json" in names or "input.json" in names
            has_failure = "failure.json" in names
            model.check(not (has_candidate and has_failure),
                        "research work item contains both candidate and pre-execution failure")

            if has_candidate:
                model.check({"input.json", "candidate.json"}.issubset(names),
                            "research work candidate lacks input or candidate")
                input_raw, input_source = fetched(base + "input.json")
                candidate_raw, candidate_source = fetched(base + "candidate.json")
                input_model = ExternalResearchInputPacket.model_validate(_json(input_raw))
                model.check(work.output_prefix(input_model, key) == base, "retained execution path differs")
                if is_child:
                    prior = [r for r in input_model.source_refs if r.purpose == "CONTINUATION_PREDECESSOR_RESULT"]
                    model.check(len(prior) == 1 and prior[0].git_blob == rows[prior[0].path]["sha"],
                                "retained continuation predecessor differs")
                outcome = work.describe_outcome(reserved_packet=packet_raw,
                                                input_raw=input_raw, candidate_raw=candidate_raw)
                validation = ExternalResearchValidationResult.model_validate(outcome["validation"])
                sources = {"packet": packet_source, "input": input_source, "candidate": candidate_source}
                if "funnel.json" in names:
                    funnel_raw, funnel_source = fetched(base + "funnel.json")
                    saved_funnel = ResearchFunnelResult.model_validate(_json(funnel_raw))
                    model.check(validation.funnel_result is not None and saved_funnel == validation.funnel_result,
                                "saved Funnel differs from original candidate revalidation")
                    sources["funnel"] = funnel_source
                if validation.funnel_result is None:
                    status = "VALIDATED_EXECUTION_GAP"
                    terminal_state = terminal_reason = None
                else:
                    status = "VALIDATED_FUNNEL_CANDIDATE"
                    terminal_state = validation.funnel_result.terminal_state.value
                    terminal_reason = validation.funnel_result.terminal_reason
                items.append({"assessment_input_hash": key, "case_id": input_model.case_id,
                              "ticker": input_model.ticker, "status": status,
                              "validation_status": validation.status.value,
                              "completion": validation.completion.value,
                              "terminal_state": terminal_state, "terminal_reason": terminal_reason,
                              "finished_at": candidate_raw and _json(candidate_raw)["receipt"]["finished_at"],
                              "semantic_acceptance": "NOT_ESTABLISHED_BY_READER",
                              "registered_current_handoff": False,
                              **model.AUTHORITY, **lineage, "sources": sources})
                continue

            if has_failure:
                failure_raw, failure_source = fetched(base + "failure.json")
                failure = _json(failure_raw)
                model.check(failure.get("schema_version") == 1
                            and failure.get("record_kind") == "PRE_EXECUTION_FAILURE_NOT_VALIDATOR_RESULT"
                            and failure.get("assessment_input_hash") == key,
                            "research work failure identity differs")
                model.check(failure.get("research_execution") == "NOT_EXECUTED"
                            and failure.get("funnel_status") == "NOT_REACHED"
                            and failure.get("formal_research_budget_used", 0) == 0,
                            "research work pre-execution failure gained Research state")
                model.check(all(failure.get(k, "NONE") == "NONE" for k in model.AUTHORITY),
                            "research work failure gained authority")
                model.check(failure.get("packet_blob") == model.blob_sha(packet_raw)
                            and failure.get("packet_sha256") == model.sha256(packet_raw),
                            "research work failure packet binding differs")
                if is_child:
                    model.check(failure.get("execution_id") == lineage["execution_id"]
                        and failure.get("continuation_permission_id") == comment_id,
                        "continuation failure identity differs")
                packet = work._packet(packet_raw)
                items.append({"assessment_input_hash": key,
                              "case_id": failure.get("case_id") or packet.stock_code,
                              "ticker": packet.stock_code, "status": "PRE_EXECUTION_FAILURE",
                              "failure_status": failure.get("status"),
                              "research_execution": "NOT_EXECUTED", "terminal_state": None,
                              "finished_at": failure.get("finished_at"),
                              "semantic_acceptance": "NOT_APPLICABLE_FAILURE_NOT_RESEARCH",
                              "registered_current_handoff": False,
                              **model.AUTHORITY, **lineage,
                              "sources": {"packet": packet_source, "failure": failure_source}})
                continue

            packet = work._packet(packet_raw)
            items.append({"assessment_input_hash": key, "case_id": packet.stock_code,
                          "ticker": packet.stock_code, "status": "RETAINED_NO_RESEARCH_RESULT",
                          "terminal_state": None, "finished_at": None,
                          "semantic_acceptance": "NOT_ESTABLISHED_BY_READER",
                          "registered_current_handoff": False,
                          **model.AUTHORITY, **lineage, "sources": {"packet": packet_source}})

        def sort_key(item: dict):
            stamp = item.get("finished_at")
            return (model.clock(stamp) if stamp else datetime.min.replace(tzinfo=timezone.utc),
                    item["assessment_input_hash"])
        items.sort(key=sort_key, reverse=True)
        counts = {name: sum(item["status"] == name for item in items) for name in (
            "VALIDATED_FUNNEL_CANDIDATE", "VALIDATED_EXECUTION_GAP",
            "PRE_EXECUTION_FAILURE", "RETAINED_NO_RESEARCH_RESULT")}
        return {"status": "READ_OK", "work_ref": work.WORK_REF, "work_commit": work_commit,
                "mode": config["mode"], "item_count": len(items), "counts": counts, "items": items,
                "meaning": "READ_ONLY_RETAINED_WORK_NOT_SEMANTIC_ACCEPTANCE_OR_HANDOFF_REGISTRATION"}

    def research(self, registry: dict, *, include_work: bool = True) -> dict:
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
        result = {"production_configuration": configuration, "production_inputs": packages,
                  "records": records,
                  "candidate_work": {"status": "NOT_CONFIGURED",
                      "meaning": "NO_AUTODISCOVERED_RESEARCH_WORK_READ_REQUESTED"},
                  "handoffs": project_registered_handoffs(entries, self.source), "gaps": gaps,
                  "confirmed_actions": [r for r in records if r["use"] == "CONFIRMED_ACTION_CHECKPOINT"],
                  "confirmed_action_scope": "EXPLICIT_REGISTRY_ONLY_NOT_PROOF_NO_TRADES_OCCURRED",
                  "scope": "EXPLICIT_CONFIG_REGISTERED_LINEAGE_AND_OPTED_IN_RETAINED_WORK_NOT_EXHAUSTIVE_RESEARCH_COVERAGE"}
        if include_work:
            self.include_research_work(registry, result)
        return result

    def include_research_work(self, registry: dict, research: dict) -> None:
        work_config = registry.get("research_work_read")
        if work_config is not None:
            try:
                research["candidate_work"] = self.research_work(work_config)
            except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError) as exc:
                research["candidate_work"] = {"status": "UNAVAILABLE_OR_REJECTED",
                    "error_type": type(exc).__name__, "meaning": "RESEARCH_WORK_NOT_QUIET_AND_NOT_PROMOTED",
                    "diagnostic": research_work_diagnostic(exc,
                        api_calls=getattr(self.api, "calls", None), source_count=len(self.sources),
                        retained_file_count=len(self.files))}
                research["gaps"].append({"status": "RESEARCH_WORK_READ_UNAVAILABLE_NOT_QUIET",
                                         "error_type": type(exc).__name__})

    def collect(self, refresh: dict) -> dict:
        started = self.now()
        raw, registry_ref = self.source({"path": REGISTRY_PATH})
        registry = json.loads(raw)
        model.check(registry["schema_version"] == 1, "registry unsupported")
        lanes = {name: self.lane(name) for name in model.WORKFLOWS}
        capabilities = []
        for item in registry["capability_gaps"]:
            try:
                _, reference = self.source(item["source"])
                capabilities.append({"id": item["id"], "status": item["status"], "source": reference})
            except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, RuntimeError):
                capabilities.append({"id": item["id"], "status": "ACCEPTANCE_SOURCE_UNAVAILABLE"})
        research = self.research(registry, include_work=False)
        research["registry"] = registry_ref
        # All baseline lanes, registered handoffs and capability references have
        # now consumed their actual budget. Optional work is always last.
        baseline_files, baseline_sources = dict(self.files), dict(self.sources)
        self.include_research_work(registry, research)

        def assembled():
            value = model.assemble(code_commit=self.code_commit, checked_at=self.now(), check_started_at=started,
                                   lanes=lanes, research=research, capabilities=capabilities, refresh_identity=refresh)
            return value, {"current-state.json": model.read_package_bytes(value),
                           "README.md": model.render_summary(value).encode()}

        payload, entry_files = assembled()
        size = sum(map(len, self.files.values())) + sum(map(len, entry_files.values()))
        if size > MAX_RETAINED_OUTPUT and research["candidate_work"]["status"] == "READ_OK":
            # Final entry size is only knowable after projection. Keep the exact
            # baseline sources and an explicit gap, rather than break delivery.
            self.files, self.sources = baseline_files, baseline_sources
            research["candidate_work"] = {"status": "UNAVAILABLE_OR_REJECTED",
                "error_type": "ReadingEntryRetentionLimit", "meaning": "RESEARCH_WORK_NOT_QUIET_AND_NOT_PROMOTED"}
            research["gaps"].append({"status": "RESEARCH_WORK_READ_UNAVAILABLE_NOT_QUIET",
                                     "error_type": "ReadingEntryRetentionLimit"})
            payload, entry_files = assembled()
        used = getattr(self.api, "calls", None)
        if type(used) is int:
            model.check(used + len(set(self.files) | set(entry_files)) + 5 <= MAX_API_CALLS,
                        "collection leaves insufficient publication API budget")
        for path, raw in entry_files.items():
            self.retain(path, raw)
        if registry.get("stock_business_work_read") is True:
            from .stock_research_reading import attach
            payload = attach(self, payload)
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
    # Baseline Collector keeps its original 180-call/60-source limits. The
    # optional Stock lane reserves its own finite additional reading/publication.
    from .stock_research_reading import EXTRA_API_CALLS
    api = GitHubAPI(os.environ["GH_TOKEN"], max_calls=MAX_API_CALLS + EXTRA_API_CALLS)
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
