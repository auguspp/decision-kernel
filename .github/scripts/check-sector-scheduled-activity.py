"""Bounded metadata observation, with scoped reconciliation of count/list drift.

Not an atomic lock. No market credential, provider request, polling or retry.
An incomplete repository listing is never interpreted as an empty peer set.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

REPOSITORY = "auguspp/decision-kernel"
PEERS = frozenset(f".github/workflows/{name}.yml" for name in (
    "decision-inbox", "hithink-stock-dump-trial", "live-dogfood",
))
ACTIVE = ("in_progress", "queued", "waiting", "pending", "requested")
MAX_BYTES = 4 * 1024 * 1024
WORKFLOW = re.compile(r"\.github/workflows/([A-Za-z0-9][A-Za-z0-9_.-]*\.ya?ml)\Z")


class CheckError(RuntimeError):
    """Only fixed, non-secret diagnostics leave this metadata precheck."""


class ActivityPage(dict):
    """Keep transport pagination outside the untrusted JSON key namespace."""
    def __init__(self, payload: dict, *, has_next: bool):
        super().__init__(payload)
        self.has_next = has_next


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CheckError("GITHUB_REDIRECT_REFUSED")


def require_invocation(env: Mapping[str, str]) -> None:
    if (env.get("GITHUB_REPOSITORY") != REPOSITORY
            or env.get("GITHUB_REF") != "refs/heads/main"
            or env.get("GITHUB_EVENT_NAME") not in {"workflow_dispatch", "schedule"}
            or env.get("GITHUB_RUN_ATTEMPT") != "1"):
        raise CheckError("FRESH_MAIN_MANUAL_OR_SCHEDULE_REQUIRED")


def _object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise CheckError("GITHUB_DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _query(url: str) -> tuple[str, str]:
    parsed = urlsplit(url)
    base = f"/repos/{REPOSITORY}/actions"
    scope = "repository"
    if parsed.path != base + "/runs":
        prefix = base + "/workflows/"
        filename = parsed.path.removeprefix(prefix).removesuffix("/runs")
        if (not parsed.path.startswith(prefix) or not parsed.path.endswith("/runs")
                or WORKFLOW.fullmatch(".github/workflows/" + filename) is None):
            raise CheckError("GITHUB_URL_NOT_ALLOWED")
        scope = filename
    query = parse_qs(parsed.query, keep_blank_values=True)
    if (parsed.scheme != "https" or parsed.netloc != "api.github.com" or parsed.fragment
            or set(query) != {"status", "per_page", "page"}
            or query["status"] not in [[status] for status in ACTIVE]
            or query["per_page"] != ["100"] or query["page"] != ["1"]):
        raise CheckError("GITHUB_URL_NOT_ALLOWED")
    return scope, query["status"][0]


def request_reader(token: str, *, observations: list | None = None) -> Callable[[str], dict]:
    if not token:
        raise CheckError("GITHUB_READ_TOKEN_MISSING")
    opener = build_opener(NoRedirect())

    def read(url: str) -> dict:
        scope, status = _query(url)
        note = {"scope": scope, "query_status": status,
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "http_status": None, "bytes": None, "body_sha256": None,
                "has_next": None, "total_count": None, "returned_rows": None}
        request = Request(url, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }, method="GET")
        try:
            with opener.open(request, timeout=10) as response:
                note["http_status"] = response.status
                if response.status != 200:
                    raise CheckError("GITHUB_ACTIVITY_HTTP_STATUS_INVALID")
                raw = response.read(MAX_BYTES + 1)
                note["bytes"] = len(raw)
                if len(raw) > MAX_BYTES:
                    raise CheckError("GITHUB_ACTIVITY_RESPONSE_OVERSIZED")
                note["body_sha256"] = hashlib.sha256(raw).hexdigest()
                link = response.headers.get("Link", "")
                relations = re.findall(r';\s*rel\s*=\s*(?:"([^"]*)"|([^,;\s]+))', link, re.IGNORECASE)
                if link and not relations:
                    raise CheckError("GITHUB_ACTIVITY_PAGINATION_INVALID")
                note["has_next"] = any("next" in (quoted or bare).lower().split()
                                       for quoted, bare in relations)
                payload = json.loads(raw, object_pairs_hook=_object)
                if not isinstance(payload, dict):
                    raise CheckError("GITHUB_ACTIVITY_RESPONSE_INVALID")
                count, rows = payload.get("total_count"), payload.get("workflow_runs")
                note["total_count"] = count if type(count) is int else None
                note["returned_rows"] = len(rows) if isinstance(rows, list) else None
                return ActivityPage(payload, has_next=note["has_next"])
        except HTTPError as exc:
            note["http_status"] = exc.code
            raise CheckError(f"GITHUB_HTTP_{exc.code}") from None
        except (URLError, OSError, ValueError) as exc:
            raise CheckError("GITHUB_ACTIVITY_REQUEST_OR_DECODE_FAILED") from None
        finally:
            note["finished_at"] = datetime.now(timezone.utc).isoformat()
            if observations is not None:
                observations.append(note)

    return read


def _inspect(payload: dict, peers: frozenset[str], *, scope: str | None = None) -> tuple[set[int], bool]:
    if not isinstance(payload, dict):
        raise CheckError("GITHUB_ACTIVITY_RESPONSE_INVALID")
    rows, count = payload.get("workflow_runs"), payload.get("total_count")
    if (not isinstance(rows, list) or type(count) is not int or count < 0
            or len(rows) > 100):
        raise CheckError("GITHUB_ACTIVITY_RESPONSE_INVALID")
    seen, blockers = set(), set()
    for row in rows:
        if (not isinstance(row, dict) or type(row.get("id")) is not int
                or row["id"] <= 0 or row["id"] in seen
                or not isinstance(row.get("path"), str) or not row["path"]
                or row.get("status") not in ACTIVE):
            raise CheckError("GITHUB_ACTIVITY_ROW_INVALID")
        seen.add(row["id"])
        path = row["path"].split("@", 1)[0]
        if scope is not None and path != scope:
            raise CheckError("GITHUB_SCOPED_ACTIVITY_IDENTITY_MISMATCH")
        if path in peers:
            blockers.add(row["id"])
    complete = count == len(rows) and not getattr(payload, "has_next", False)
    return blockers, complete


def check_activity(read: Callable[[str], dict], *, peers: frozenset[str] = PEERS) -> list[int]:
    """Five fast-path GETs; at most 5*len(peers) scoped GETs if reconciliation is needed.

    A scoped observation replaces uncertain repository-wide visibility, not source
    qualification. It remains non-atomic; observed blockers are never discarded.
    No HTTP/transport/malformed-response error invokes the scoped path.
    """
    if (not isinstance(peers, frozenset) or not peers or len(peers) > 8
            or any(not isinstance(p, str) or WORKFLOW.fullmatch(p) is None for p in peers)):
        raise CheckError("ACTIVITY_PEERS_INVALID")
    base = f"https://api.github.com/repos/{REPOSITORY}/actions"
    blockers = set()
    for status in ACTIVE:
        query = urlencode({"status": status, "per_page": 100, "page": 1})
        found, complete = _inspect(read(f"{base}/runs?{query}"), peers)
        blockers.update(found)
        if not complete:
            break
    else:
        return sorted(blockers)

    # Re-observe ALL active statuses for the actual key-sharing workflows. Do not
    # merely accept an inconsistent empty page or repeat the same broad query.
    for peer in sorted(peers):
        filename = WORKFLOW.fullmatch(peer).group(1)
        for status in ACTIVE:
            query = urlencode({"status": status, "per_page": 100, "page": 1})
            found, complete = _inspect(read(f"{base}/workflows/{filename}/runs?{query}"), peers, scope=peer)
            blockers.update(found)
            if not complete:
                raise CheckError("GITHUB_SCOPED_ACTIVITY_RESPONSE_INCOMPLETE")
    return sorted(blockers)


def main() -> int:
    started = datetime.now(timezone.utc).isoformat()
    observations, blockers = [], []
    try:
        require_invocation(os.environ)
        blockers = check_activity(request_reader(os.environ.get("GITHUB_TOKEN", ""), observations=observations))
        message = ("BLOCKED_SHARED_KEY_ACTIVITY run_ids=" + ",".join(map(str, blockers))
                   if blockers else "NO_VISIBLE_PEER_ACTIVITY_NOT_A_GLOBAL_LOCK")
        code = 2 if blockers else 0
    except CheckError as exc:
        message, code = str(exc), 2
    finished = datetime.now(timezone.utc).isoformat()
    receipt = {"started_at": started, "finished_at": finished, "result": message,
               "exit_code": code, "blocker_run_ids": blockers, "observations": observations,
               "market_requests": 0, "atomic_lock": False}
    text = (f"### Shared-Key activity precheck\n\n{message}\n\n"
            f"Checked UTC: {started} → {finished}. No market request or retry.\n\n"
            "This is a non-atomic repository observation, not provider-quota proof or a global Key lock.\n\n"
            + "```json\n" + json.dumps(receipt, sort_keys=True) + "\n```\n")
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as output:
            output.write(text)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
