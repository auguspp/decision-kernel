"""One bounded GitHub metadata observation before either Sector trigger.

Not a lock or a scheduler: peers/external consumers may start after this check.
No HiThink credential, quota probe, polling, retry, dispatch or state write.
"""
from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

REPOSITORY = "auguspp/decision-kernel"
PEERS = frozenset(f".github/workflows/{name}.yml" for name in (
    "decision-inbox", "hithink-stock-dump-trial", "live-dogfood",
))
ACTIVE = ("in_progress", "queued", "waiting", "pending", "requested")
MAX_BYTES = 4 * 1024 * 1024


class CheckError(RuntimeError):
    """Only fixed, non-secret diagnostics leave this metadata precheck."""


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


def request_reader(token: str) -> Callable[[str], dict]:
    if not token:
        raise CheckError("GITHUB_READ_TOKEN_MISSING")
    opener = build_opener(NoRedirect())

    def read(url: str) -> dict:
        if not url.startswith(f"https://api.github.com/repos/{REPOSITORY}/actions/runs?"):
            raise CheckError("GITHUB_URL_NOT_ALLOWED")
        request = Request(url, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }, method="GET")
        try:
            with opener.open(request, timeout=10) as response:
                raw = response.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES or 'rel="next"' in response.headers.get("Link", ""):
                    raise CheckError("GITHUB_ACTIVITY_RESPONSE_INCOMPLETE")
                return json.loads(raw, object_pairs_hook=_object)
        except HTTPError as exc:
            raise CheckError(f"GITHUB_HTTP_{exc.code}") from None
        except (URLError, OSError, ValueError) as exc:
            raise CheckError("GITHUB_ACTIVITY_REQUEST_OR_DECODE_FAILED") from None

    return read


def check_activity(read: Callable[[str], dict], *, peers: frozenset[str] = PEERS) -> list[int]:
    """At most five single-page GETs; incomplete visibility fails closed."""
    blockers = set()
    for status in ACTIVE:
        query = urlencode({"status": status, "per_page": 100, "page": 1})
        payload = read(f"https://api.github.com/repos/{REPOSITORY}/actions/runs?{query}")
        if not isinstance(payload, dict):
            raise CheckError("GITHUB_ACTIVITY_RESPONSE_INVALID")
        rows, count = payload.get("workflow_runs"), payload.get("total_count")
        if (not isinstance(rows, list) or type(count) is not int
                or not 0 <= count <= 100 or len(rows) != count):
            raise CheckError("GITHUB_ACTIVITY_RESPONSE_INCOMPLETE")
        seen = set()
        for row in rows:
            if (not isinstance(row, dict) or type(row.get("id")) is not int
                    or row["id"] <= 0 or row["id"] in seen
                    or not isinstance(row.get("path"), str) or not row["path"]
                    or row.get("status") not in ACTIVE):
                raise CheckError("GITHUB_ACTIVITY_ROW_INVALID")
            seen.add(row["id"])
            if row["path"].split("@", 1)[0] in peers:
                blockers.add(row["id"])
    return sorted(blockers)


def main() -> int:
    started = datetime.now(timezone.utc).isoformat()
    try:
        require_invocation(os.environ)
        blockers = check_activity(request_reader(os.environ.get("GITHUB_TOKEN", "")))
        message = ("BLOCKED_SHARED_KEY_ACTIVITY run_ids=" + ",".join(map(str, blockers))
                   if blockers else "NO_VISIBLE_PEER_ACTIVITY_NOT_A_GLOBAL_LOCK")
        code = 2 if blockers else 0
    except CheckError as exc:
        message, code = str(exc), 2
    finished = datetime.now(timezone.utc).isoformat()
    text = (f"### Shared-Key activity precheck\n\n{message}\n\n"
            f"Checked UTC: {started} → {finished}. No market request or retry.\n\n"
            "This is a non-atomic repository observation, not provider-quota proof or a global Key lock.\n\n")
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as output:
            output.write(text)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
