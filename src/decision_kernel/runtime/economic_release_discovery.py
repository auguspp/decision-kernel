from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Mapping, Sequence
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import ProxyHandler, Request, build_opener
from zoneinfo import ZoneInfo

from decision_kernel.identity import canonical_hash, canonical_json
from .economic_node_study import AUTHORITY, qualify_release_excerpt
from .economic_source_capture import (
    EconomicCaptureError, EconomicRedirectError, PublicResponse, _NoRedirect,
    _safe_headers, decode_page,
)


SCHEMA = 1
SEMANTICS = "BOUNDED_VISIBLE_DIRECTORY_DISCOVERY_TO_UNREVIEWED_SOURCE_PACKETS"
POLICY = "moa-feed-spb-monthly-visible-window-v1"
DIRECTORIES = {
    "MOA_FEED": "https://xmsyj.moa.gov.cn/jcyj/",
    "SPB_EXPRESS": "https://www.spb.gov.cn/gjyzj/c100015/c100016/common_list.shtml",
}
PATHS = {
    "MOA_FEED": r"/jcyj/[0-9]{6}/t[0-9]{8}_[0-9]+\.htm",
    "SPB_EXPRESS": r"/gjyzj/c100015/c100016/[0-9]{6}/[0-9a-f]{32}\.shtml",
}
TITLES = {
    "MOA_FEED": r"(?:[0-9]{4}年)?(?:[1-9]|1[0-2])月第[1-5]周畜产品和饲料集贸市场价格情况",
    "SPB_EXPRESS": r"国家邮政局公布[0-9]{4}年(?:1-(?:[1-9]|1[0-2])月|(?:[1-9]|1[0-2])月|上半年)邮政行业运行情况",
}
LIVE = "PUBLIC_HTTP_DISCOVERY"
SYNTHETIC = "SYNTHETIC_TEST_ONLY"
MAX_BODY = 2 * 1024 * 1024
MAX_ARCHIVE = 20 * 1024 * 1024
MAX_DETAIL_REQUESTS = 4
MAX_DIRECTORY_ROWS = 100
SHANGHAI = ZoneInfo("Asia/Shanghai")


class ReleaseDiscoveryError(ValueError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bytes(value) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def _aware(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ReleaseDiscoveryError("timezone-aware capture clock required")
    return value


def _compact(text: str) -> str:
    return "".join(text.split())


def _article_url(family: str, url: str) -> str:
    part = urlsplit(url)
    directory = urlsplit(DIRECTORIES[family])
    if (part.scheme != "https" or part.netloc != directory.netloc or part.query or part.fragment
            or not re.fullmatch(PATHS[family], part.path)):
        raise ReleaseDiscoveryError("article URL is outside the exact reviewed source family")
    return url


def _family(url: str) -> str:
    for family in DIRECTORIES:
        try:
            _article_url(family, url)
            return family
        except ReleaseDiscoveryError:
            pass
    raise ReleaseDiscoveryError("unrecognized reviewed source URL")


def _implementation() -> dict:
    package = Path(__file__).resolve().parents[1]
    names = ("identity.py", "runtime/economic_node_study.py", "runtime/economic_source_capture.py",
             "runtime/economic_release_discovery.py")
    return {name: _sha((package / name).read_bytes()) for name in names}


def _decoded(response: PublicResponse) -> str:
    # Reuse strict HTML/status/size/header/encoding checks. This parser slice accepts
    # UTF-8 only; unsupported encodings remain explicit rather than guessed.
    decode_page(response)
    try:
        return response.body.decode("utf-8-sig")
    except UnicodeError as exc:
        raise ReleaseDiscoveryError("directory/detail link parser requires valid UTF-8") from exc


class _DirectoryRows(HTMLParser):
    """Extract li-local anchors and dates; never associate a date across rows."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.stack = []
        self.anchor = None
        self.ignored = []
        self.base_seen = False

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "template", "noscript"}:
            self.ignored.append(tag)
        if self.ignored:
            return
        if tag == "base":
            self.base_seen = True
        if tag == "li":
            self.stack.append({"anchors": [], "text": [], "line": self.getpos()[0]})
        if tag == "a" and self.stack:
            if self.anchor is not None:
                raise ReleaseDiscoveryError("nested directory anchors")
            values = dict(attrs)
            if len(values) != len(attrs):
                raise ReleaseDiscoveryError("duplicate directory attributes")
            self.anchor = {"href": values.get("href", ""), "title": values.get("title", ""),
                           "text": [], "line": self.getpos()[0], "column": self.getpos()[1]}

    def handle_endtag(self, tag):
        if self.ignored:
            if tag == self.ignored[-1]:
                self.ignored.pop()
            return
        if tag == "a" and self.anchor is not None:
            if not self.stack:
                raise ReleaseDiscoveryError("anchor without a list row")
            self.stack[-1]["anchors"].append(self.anchor)
            self.anchor = None
        if tag == "li" and self.stack:
            if self.anchor is not None:
                raise ReleaseDiscoveryError("unclosed directory anchor")
            self.rows.append(self.stack.pop())

    def handle_data(self, data):
        if self.ignored:
            return
        if self.stack:
            self.stack[-1]["text"].append(data)
        if self.anchor is not None:
            self.anchor["text"].append(data)


def parse_directory(family: str, response: PublicResponse, *, captured_at: datetime) -> dict:
    if response.url != DIRECTORIES[family]:
        raise ReleaseDiscoveryError("directory response identity changed")
    local_date = _aware(captured_at).astimezone(SHANGHAI).date()
    parser = _DirectoryRows()
    parser.feed(_decoded(response))
    parser.close()
    if parser.stack or parser.anchor or parser.ignored or parser.base_seen:
        raise ReleaseDiscoveryError("unclosed directory markup or unsupported base URL")
    rows = []
    by_url = {}
    for row in parser.rows:
        links = []
        for anchor in row["anchors"]:
            visible = _compact("".join(anchor["text"]))
            title = _compact(anchor["title"] or visible)
            href = anchor["href"]
            if not isinstance(href, str) or not isinstance(title, str):
                raise ReleaseDiscoveryError("malformed directory anchor")
            absolute = urljoin(response.url, href)
            try:
                _article_url(family, absolute)
            except ReleaseDiscoveryError:
                if re.fullmatch(TITLES[family], title):
                    raise ReleaseDiscoveryError("target title points outside its allowed article family")
                continue
            if not title or len(title) > 300 or any(ord(c) < 32 for c in title):
                raise ReleaseDiscoveryError("invalid directory title")
            links.append((absolute, title, anchor))
        if not links:
            continue
        if len(links) != 1:
            raise ReleaseDiscoveryError("ambiguous article/date association within directory row")
        days = set(re.findall(r"(?<![0-9])[0-9]{4}-[0-9]{2}-[0-9]{2}(?![0-9])", "".join(row["text"])))
        if len(days) != 1:
            raise ReleaseDiscoveryError("directory article requires exactly one explicit full date")
        published = date.fromisoformat(next(iter(days)))
        if published > local_date:
            raise ReleaseDiscoveryError("directory publication date is in the future")
        url, title, anchor = links[0]
        # Some list templates include the date inside the anchor itself.
        title = re.sub(re.escape(published.isoformat()) + r"$", "", title).strip()
        item = {"family": family, "source_url": url, "title": title,
                "listed_publication_date": published.isoformat(),
                "date_precision": "DATE_ONLY", "directory_capture_at": captured_at.isoformat(),
                "directory_body_sha256": _sha(response.body), "anchor_line": anchor["line"],
                "anchor_column": anchor["column"], "target_family": bool(re.fullmatch(TITLES[family], title))}
        signature = (title, published.isoformat())
        if url in by_url:
            if by_url[url] != signature:
                raise ReleaseDiscoveryError("duplicate URL has conflicting directory metadata")
            continue
        by_url[url] = signature
        rows.append(item)
    if not rows or len(rows) > MAX_DIRECTORY_ROWS:
        raise ReleaseDiscoveryError("directory has no qualified dated rows or exceeds row budget")
    rows.sort(key=lambda row: (row["listed_publication_date"], row["source_url"]), reverse=True)
    return {"family": family, "directory_url": response.url, "status": "PARSED_VISIBLE_WINDOW",
            "coverage": "FIRST_PAGE_ONLY_NOT_COMPLETE_RELEASE_HISTORY",
            "oldest_listed_date": min(row["listed_publication_date"] for row in rows),
            "newest_listed_date": max(row["listed_publication_date"] for row in rows), "rows": rows}


def _baseline(sources: Sequence[Mapping]) -> tuple[dict, dict]:
    if not isinstance(sources, list) or not 1 <= len(sources) <= 100:
        raise ReleaseDiscoveryError("explicit reviewed baseline must contain 1-100 source records")
    known, cutoffs = {}, {}
    for source in sources:
        qualify_release_excerpt(source)
        if source["capture_method"] != "REVIEWED_OFFICIAL_WEB_EXCERPT":
            raise ReleaseDiscoveryError("baseline requires reviewed official source records")
        url = source["source_url"]
        family = _family(url)
        if url in known or not re.fullmatch(TITLES[family], _compact(source["title"])):
            raise ReleaseDiscoveryError("baseline identity is repeated or outside target title family")
        known[url] = source
        cutoffs[family] = max(cutoffs.get(family, ""), source["published_date"])
    if set(cutoffs) != set(DIRECTORIES):
        raise ReleaseDiscoveryError("each directory needs an explicit reviewed baseline")
    return known, cutoffs


def discovery_plan(sources: list, directories: list) -> dict:
    known, cutoffs = _baseline(sources)
    entries, selected = [], []
    for directory in directories:
        if directory["status"] != "PARSED_VISIBLE_WINDOW":
            continue
        for row in directory["rows"]:
            if not row["target_family"] and row["source_url"] not in known:
                continue
            prior = known.get(row["source_url"])
            if prior is not None:
                same = (_compact(prior["title"]) == row["title"] and
                        prior["published_date"] == row["listed_publication_date"])
                disposition = "KNOWN_URL_NOT_REVALIDATED" if same else "KNOWN_METADATA_CHANGED_REVIEW_REQUIRED"
            elif row["listed_publication_date"] < cutoffs[row["family"]]:
                disposition = "OLDER_UNREVIEWED_BACKLOG_NOT_FETCHED"
            else:
                disposition = "UNREVIEWED_RELEASE_AT_OR_AFTER_BASELINE"
            item = {**row, "baseline_latest_publication_date": cutoffs[row["family"]],
                    "discovery_disposition": disposition}
            entries.append(item)
            if disposition in {"UNREVIEWED_RELEASE_AT_OR_AFTER_BASELINE", "KNOWN_METADATA_CHANGED_REVIEW_REQUIRED"}:
                selected.append(item)
    selected.sort(key=lambda row: (row["family"], row["listed_publication_date"], row["source_url"]))
    within_budget = len(selected) <= MAX_DETAIL_REQUESTS
    return {"entries": entries, "detail_candidates": selected,
            "detail_requests": [row["source_url"] for row in selected] if within_budget else [],
            "budget_status": "WITHIN_BUDGET" if within_budget else "BUDGET_EXCEEDED_NO_DETAILS_FETCHED",
            "max_detail_requests": MAX_DETAIL_REQUESTS, "candidate_count": len(selected)}


class _ArticleMetadata(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.values = {}

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        values = dict(attrs)
        name = (values.get("name") or "").lower()
        if name not in {"articletitle", "pubdate"}:
            return
        if len(values) != len(attrs) or name in self.values:
            raise ReleaseDiscoveryError("ambiguous article identity metadata")
        self.values[name] = values.get("content", "")


def review_packet(item: Mapping, response: PublicResponse, *, acquired_at: datetime) -> dict:
    if response.url != item["source_url"]:
        raise ReleaseDiscoveryError("detail response URL differs from the discovered URL")
    parser = _ArticleMetadata()
    parser.feed(_decoded(response))
    parser.close()
    title = _compact(parser.values.get("articletitle", ""))
    published = parser.values.get("pubdate", "")
    if (title != item["title"] or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?: [0-9]{2}:[0-9]{2}:[0-9]{2})?", published)
            or published[:10] != item["listed_publication_date"]):
        raise ReleaseDiscoveryError("article title/date do not corroborate directory identity")
    if _aware(acquired_at) < datetime.fromisoformat(item["directory_capture_at"]):
        raise ReleaseDiscoveryError("article capture predates directory discovery")
    return {"source_url": item["source_url"], "family": item["family"], "title": title,
            "listed_publication_date": item["listed_publication_date"], "date_precision": "DATE_ONLY",
            "directory_observed_at": item["directory_capture_at"], "content_acquired_at": acquired_at.isoformat(),
            "raw_body_sha256": _sha(response.body), "directory_body_sha256": item["directory_body_sha256"],
            "status": "PENDING_HUMAN_SOURCE_REVIEW", "metrics_extracted": False,
            "historical_first_vintage_proven": False, "economic_observation_written": False,
            "source_packet_id": canonical_hash({"url": response.url, "body": _sha(response.body)}), **AUTHORITY}


def fetch_discovery_page(url: str) -> PublicResponse:
    if url not in DIRECTORIES.values():
        _family(url)
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    request = Request(url, headers={"User-Agent": "decision-kernel-public-source-study/1.0",
                      "Accept": "text/html,application/xhtml+xml", "Accept-Encoding": "identity"})
    with opener.open(request, timeout=20) as response:
        headers = _safe_headers(dict(response.headers.items()))
        length = headers.get("content-length")
        if length is not None and (not re.fullmatch(r"[0-9]+", length) or int(length) > MAX_BODY):
            raise ReleaseDiscoveryError("declared body exceeds discovery budget")
        body = response.read(MAX_BODY + 1)
        if len(body) > MAX_BODY:
            raise ReleaseDiscoveryError("body exceeds discovery budget")
        return PublicResponse(response.geturl(), response.status, headers, body)


def _result(sources: list, acquisitions: list, provenance: str) -> dict:
    _baseline(sources)
    if any(datetime.fromisoformat(source["captured_at"].replace("Z", "+00:00")) > datetime.fromisoformat(acquisitions[0]["record"]["started_at"]) for source in sources):
        raise ReleaseDiscoveryError("baseline knowledge postdates directory scan")
    directories = []
    for (family, url), acquisition in zip(DIRECTORIES.items(), acquisitions[:2], strict=True):
        if acquisition["url"] != url:
            raise ReleaseDiscoveryError("directory request order/identity disagrees")
        record = acquisition["record"]
        try:
            if acquisition["response"] is None:
                raise ReleaseDiscoveryError("directory transport unavailable")
            parsed = parse_directory(family, acquisition["response"],
                                     captured_at=datetime.fromisoformat(record["completed_at"]))
        except (ValueError, RuntimeError) as exc:
            parsed = {"family": family, "directory_url": url, "status": "UNAVAILABLE_OR_UNPARSEABLE",
                      "error_type": type(exc).__name__, "diagnostic": str(exc) if isinstance(exc, (ReleaseDiscoveryError, EconomicCaptureError)) else "directory parsing rejected", "rows": [],
                      "coverage": "UNKNOWN_NOT_A_NO_NEW_RELEASE_RESULT"}
        directories.append(parsed)
    plan = discovery_plan(sources, directories)
    expected = list(DIRECTORIES.values()) + plan["detail_requests"]
    if [item["url"] for item in acquisitions] != expected:
        raise ReleaseDiscoveryError("detail requests differ from the exact bounded discovery plan")
    packets = []
    for item, acquisition in zip(plan["detail_candidates"] if plan["detail_requests"] else [], acquisitions[2:], strict=True):
        try:
            if acquisition["response"] is None:
                raise ReleaseDiscoveryError("detail transport unavailable")
            packet = review_packet(item, acquisition["response"],
                                   acquired_at=datetime.fromisoformat(acquisition["record"]["completed_at"]))
        except (ValueError, RuntimeError) as exc:
            packet = {"source_url": item["source_url"], "status": "SOURCE_IDENTITY_OR_TRANSPORT_REVIEW_REQUIRED",
                      "error_type": type(exc).__name__, "metrics_extracted": False, **AUTHORITY}
        packets.append(packet)
    complete = (all(row["status"] == "PARSED_VISIBLE_WINDOW" for row in directories)
                and plan["budget_status"] == "WITHIN_BUDGET"
                and all(row["status"] == "PENDING_HUMAN_SOURCE_REVIEW" for row in packets))
    return {"schema_version": SCHEMA, "policy": POLICY, "semantics": SEMANTICS, "provenance": provenance,
            "status": "COMPLETE_BOUNDED_SCAN" if complete else "INCOMPLETE",
            "baseline_hash": canonical_hash(sources), "directories": directories, "plan": plan,
            "review_packets": packets, "complete_publisher_coverage": False,
            "observation_writes": 0, "market_event_writes": 0, "automatic_review_acceptance": False,
            "known_url_body_revisions_checked": False, **AUTHORITY}


def _summary(result: Mapping) -> str:
    lines = ["## Official release discovery — " + result["status"], "",
             "仅扫描两个官方目录的当前可见页；不是完整发布历史，也不是已经审阅的经济信号。", ""]
    for directory in result["directories"]:
        lines.append(f"- {directory['family']}: {directory['status']}; visible dated rows={len(directory['rows'])}.")
    lines += ["", f"Unreviewed detail candidates: {result['plan']['candidate_count']}; {result['plan']['budget_status']}.",
              "", "### Unreviewed source packets"]
    for packet in result["review_packets"]:
        lines.append(f"- {html.escape(packet.get('title', packet['source_url']))}: {packet['status']}.")
    if not result["review_packets"]:
        lines.append("No new review packet was produced in this visible scope. This is not proof of no publisher update.")
    lines += ["", "已知URL未重新读取正文，不能据此排除修订。旧的未审阅页面作为backlog保留，不冒充最新消息。",
              "不自动提取或接受经济数值，不写入市场事件，不更新研究结论。", "",
              "SHADOW OBSERVATION ONLY · HUMAN ATTENTION AUTHORITY = NONE · RESEARCH AUTHORITY = NONE · INVESTMENT AUTHORITY = NONE", ""]
    return "\n".join(lines)


def run_discovery(sources: list, root: Path, *, transport: Callable | None = None,
                  provenance: str = LIVE, now: Callable | None = None) -> dict:
    _baseline(sources)
    if provenance not in {LIVE, SYNTHETIC} or ((transport is not None) != (provenance == SYNTHETIC)):
        raise ReleaseDiscoveryError("injected transport requires explicit synthetic provenance")
    if root.exists() or any(path.is_symlink() for path in (root, *root.parents)) or "decision-state" in root.resolve().parts:
        raise ReleaseDiscoveryError("use a new non-market archive directory without symlinks")
    now = now or (lambda: datetime.now(timezone.utc))
    initial_clock = _aware(now())
    if any(datetime.fromisoformat(source["captured_at"].replace("Z", "+00:00")) > initial_clock for source in sources):
        raise ReleaseDiscoveryError("reviewed baseline was acquired after the scan clock")
    root.mkdir(parents=True, exist_ok=False)
    transport = transport or fetch_discovery_page
    acquisitions, files = [], {}

    def put(name, data):
        if len(data) > MAX_BODY or sum(row["bytes"] for row in files.values()) + len(data) > MAX_ARCHIVE:
            raise ReleaseDiscoveryError("discovery archive budget exceeded")
        (root / name).write_bytes(data)
        files[name] = {"bytes": len(data), "sha256": _sha(data)}

    def acquire(url):
        index = len(acquisitions)
        start = _aware(now())
        response = None
        code, error = None, None
        try:
            response = transport(url)
            if (type(response.status) is not int or not 100 <= response.status <= 599
                    or not isinstance(response.body, bytes) or len(response.body) > MAX_BODY):
                raise ReleaseDiscoveryError("malformed or over-budget HTTP response")
            response = PublicResponse(response.url, response.status, _safe_headers(response.headers), response.body)
            code = response.status
        except (OSError, ValueError, RuntimeError) as exc:
            response = None
            error = type(exc).__name__
            if isinstance(exc, HTTPError):
                code = exc.code if type(exc.code) is int and 300 <= exc.code <= 599 else None
                try:
                    exc.close()
                except (OSError, ValueError):
                    pass
            elif isinstance(exc, EconomicRedirectError):
                code = exc.http_status
        end = _aware(now())
        if end < start or (acquisitions and start < datetime.fromisoformat(acquisitions[-1]["record"]["completed_at"])):
            raise ReleaseDiscoveryError("reversed acquisition clocks")
        record = {"url": url, "started_at": start.isoformat(), "completed_at": end.isoformat(),
                  "http_status": code, "error_type": error, "body_retained": response is not None}
        if response is not None:
            put(f"{index:02d}.body.bin", response.body)
            put(f"{index:02d}.response.json", _bytes({"url": response.url, "status": response.status, "headers": dict(response.headers)}))
        put(f"{index:02d}.request.json", _bytes(record))
        acquisitions.append({"url": url, "record": record, "response": response})

    put("baseline.json", _bytes(sources))
    for url in DIRECTORIES.values():
        acquire(url)
    # Build a directory-only plan before any article requests. The same function
    # reconstructs it during verification; budgets never select a top-N subset.
    directories = []
    for (family, url), acquisition in zip(DIRECTORIES.items(), acquisitions, strict=True):
        try:
            if acquisition["response"] is None:
                raise ReleaseDiscoveryError("unavailable directory")
            value = parse_directory(family, acquisition["response"],
                                    captured_at=datetime.fromisoformat(acquisition["record"]["completed_at"]))
        except (ValueError, RuntimeError):
            value = {"family": family, "status": "UNAVAILABLE_OR_UNPARSEABLE", "rows": []}
        directories.append(value)
    plan = discovery_plan(sources, directories)
    for url in plan["detail_requests"]:
        acquire(url)
    result = _result(sources, acquisitions, provenance)
    put("result.json", _bytes(result))
    put("summary.md", _summary(result).encode("utf-8"))
    manifest = {"schema_version": SCHEMA, "policy": POLICY, "semantics": SEMANTICS,
                "provenance": provenance, "request_count": len(acquisitions), "files": files,
                "implementation": _implementation(), "status": result["status"], **AUTHORITY}
    manifest["archive_hash"] = canonical_hash(manifest)
    (root / "manifest.json").write_bytes(_bytes(manifest))
    return result


def verify_discovery(root: Path) -> dict:
    if any(path.is_symlink() for path in (root, *root.parents)) or (root / "manifest.json").stat().st_size > 65536:
        raise ReleaseDiscoveryError("invalid discovery archive root/manifest")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    claimed = manifest.pop("archive_hash")
    if (set(manifest) != {"schema_version", "policy", "semantics", "provenance", "request_count", "files", "implementation", "status", *AUTHORITY}
            or canonical_hash(manifest) != claimed or type(manifest["schema_version"]) is not int
            or manifest["schema_version"] != SCHEMA or manifest["policy"] != POLICY or manifest["semantics"] != SEMANTICS
            or manifest["provenance"] not in {LIVE, SYNTHETIC} or manifest["implementation"] != _implementation()
            or any(manifest[key] != value for key, value in AUTHORITY.items())):
        raise ReleaseDiscoveryError("archive identity/hash/implementation differs")
    count = manifest["request_count"]
    if type(count) is not int or not 2 <= count <= 2 + MAX_DETAIL_REQUESTS:
        raise ReleaseDiscoveryError("invalid request count")
    allowed = {"baseline.json", "result.json", "summary.md"}
    allowed |= {f"{i:02d}.{suffix}" for i in range(count) for suffix in ("request.json", "response.json", "body.bin")}
    if not set(manifest["files"]) <= allowed:
        raise ReleaseDiscoveryError("file outside bounded archive inventory")
    actual = set()
    for path in root.rglob("*"):
        if path.is_symlink() or path.is_dir():
            raise ReleaseDiscoveryError("unexpected directory or symlink")
        actual.add(path.name)
    if actual != {"manifest.json", *manifest["files"]}:
        raise ReleaseDiscoveryError("archive inventory differs")
    total = 0
    for name, entry in manifest["files"].items():
        if set(entry) != {"bytes", "sha256"} or type(entry["bytes"]) is not int or not 0 <= entry["bytes"] <= MAX_BODY:
            raise ReleaseDiscoveryError("invalid file entry")
        total += entry["bytes"]
        path = root / name
        if path.stat().st_size != entry["bytes"] or _sha(path.read_bytes()) != entry["sha256"]:
            raise ReleaseDiscoveryError("file size/hash differs")
    if total > MAX_ARCHIVE:
        raise ReleaseDiscoveryError("archive exceeds budget")
    sources = json.loads((root / "baseline.json").read_text(encoding="utf-8"))
    acquisitions = []
    for index in range(count):
        record = json.loads((root / f"{index:02d}.request.json").read_text(encoding="utf-8"))
        if set(record) != {"url", "started_at", "completed_at", "http_status", "error_type", "body_retained"} or type(record["body_retained"]) is not bool:
            raise ReleaseDiscoveryError("request record fields differ")
        start, end = [_aware(datetime.fromisoformat(record[field])) for field in ("started_at", "completed_at")]
        if end < start or (acquisitions and start < datetime.fromisoformat(acquisitions[-1]["record"]["completed_at"])):
            raise ReleaseDiscoveryError("request clocks are reversed")
        code = record["http_status"]
        if code is not None and (type(code) is not int or not 100 <= code <= 599):
            raise ReleaseDiscoveryError("invalid numeric HTTP status")
        if record["error_type"] == "HTTPError" and code is not None and code < 300:
            raise ReleaseDiscoveryError("HTTP error has a non-error status")
        if record["error_type"] == "EconomicRedirectError" and code is not None and not 300 <= code <= 399:
            raise ReleaseDiscoveryError("redirect has a non-redirect status")
        response = None
        if record["body_retained"]:
            meta = json.loads((root / f"{index:02d}.response.json").read_text(encoding="utf-8"))
            if (set(meta) != {"url", "status", "headers"} or meta["headers"] != _safe_headers(meta["headers"])
                    or type(meta["status"]) is not int or meta["status"] != code or record["error_type"] is not None):
                raise ReleaseDiscoveryError("response metadata differs from request")
            response = PublicResponse(meta["url"], meta["status"], meta["headers"], (root / f"{index:02d}.body.bin").read_bytes())
        elif (not isinstance(record["error_type"], str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,79}", record["error_type"])
              or any((root / f"{index:02d}.{suffix}").exists() for suffix in ("response.json", "body.bin"))):
            raise ReleaseDiscoveryError("unavailable response has invalid error/body records")
        acquisitions.append({"url": record["url"], "record": record, "response": response})
    result = _result(sources, acquisitions, manifest["provenance"])
    if ((root / "result.json").read_bytes() != _bytes(result)
            or (root / "summary.md").read_bytes() != _summary(result).encode("utf-8") or result["status"] != manifest["status"]):
        raise ReleaseDiscoveryError("discovery outputs do not reconstruct from original directory/detail bodies")
    return {"archive_hash": claimed, "archive_integrity": "VERIFIED", "status": result["status"],
            "review_packet_count": len(result["review_packets"]), "network_calls": 0, "production_state_writes": 0, **AUTHORITY}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Bounded official-directory discovery; no automatic economic fact acceptance.")
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("scan")
    capture.add_argument("baseline", type=Path)
    capture.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("archive", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "scan":
            if args.baseline.stat().st_size > 256 * 1024 or args.baseline.resolve().is_relative_to(args.output.resolve()):
                raise ReleaseDiscoveryError("oversized or unsafe baseline path")
            result = run_discovery(json.loads(args.baseline.read_text(encoding="utf-8")), args.output)
        else:
            result = verify_discovery(args.archive)
        print(canonical_json({key: result[key] for key in ("status",)}) if args.command == "scan" else canonical_json(result))
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        parser.exit(2, f"Release discovery unavailable: {type(exc).__name__}\n")
    return 0 if result["status"] == "COMPLETE_BOUNDED_SCAN" else 2


if __name__ == "__main__":
    raise SystemExit(main())
