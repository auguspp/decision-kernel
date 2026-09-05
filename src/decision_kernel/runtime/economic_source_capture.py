from __future__ import annotations

import argparse
import codecs
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import Message
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Mapping, Sequence
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from decision_kernel.identity import canonical_hash, canonical_json
from .economic_node_study import AUTHORITY, qualify_release_excerpt


MAX_SOURCES = 4
MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
SEMANTICS = "BOUNDED_OFFICIAL_HTML_CAPTURE_AND_REVIEWED_EXCERPT_BINDING_ONLY"
LIVE = "PUBLIC_HTTP_CAPTURE"
SYNTHETIC = "SYNTHETIC_TEST_ONLY"
HEADERS = {"content-type", "content-length", "content-encoding", "date", "last-modified", "etag"}
FILES = {"source.json", "response.bin", "response.json", "page.txt", "binding.json", "observation.json"}
MATCHED = "MATCHED_REVIEWED_EXCERPT"


class EconomicCaptureError(ValueError):
    pass


@dataclass(frozen=True)
class PublicResponse:
    url: str
    status: int
    headers: Mapping[str, str]
    body: bytes


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise EconomicCaptureError("redirect requires explicit source review")


def _clock(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise EconomicCaptureError("capture clock must be timezone-aware")
    return value


def _bytes(value) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _implementation() -> dict[str, str]:
    package = Path(__file__).resolve().parents[1]
    names = ("identity.py", "runtime/economic_node_study.py", "runtime/economic_source_capture.py")
    return {name: _sha((package / name).read_bytes()) for name in names}


def _safe_headers(headers: Mapping[str, str]) -> dict[str, str]:
    output = {}
    for name, value in headers.items():
        if not isinstance(name, str):
            raise EconomicCaptureError("malformed response header name")
        key = name.lower()
        if key not in HEADERS:
            continue
        if key in output or not isinstance(value, str) or len(value) > 2048 or "\r" in value or "\n" in value:
            raise EconomicCaptureError("malformed or repeated response metadata")
        output[key] = value
    return output


def _body_integrity(body: bytes, headers: Mapping[str, str]) -> None:
    if not isinstance(body, bytes) or not 0 < len(body) <= MAX_BODY_BYTES:
        raise EconomicCaptureError("response body is empty or exceeds the byte budget")
    length = headers.get("content-length")
    if length is not None and (not re.fullmatch(r"[0-9]+", length) or int(length) != len(body)):
        raise EconomicCaptureError("response body length disagrees with Content-Length")


def fetch_public_page(url: str) -> PublicResponse:
    """One credential-free request; URL must first pass the reviewed-source parser.

    No cookie jar, proxy/environment credentials, redirects, retries, browser code
    execution or linked-resource requests. Failed responses do not become data.
    """
    from urllib.parse import urlsplit
    parsed = urlsplit(url)
    patterns = {
        "xmsyj.moa.gov.cn": r"/jcyj/[0-9]{6}/t[0-9]{8}_[0-9]+\.htm",
        "www.spb.gov.cn": r"/gjyzj/c100015/c100016/[0-9]{6}/[0-9a-f]{32}\.shtml",
    }
    if (parsed.scheme != "https" or parsed.netloc not in patterns or parsed.query or parsed.fragment
            or not re.fullmatch(patterns[parsed.netloc], parsed.path)):
        raise EconomicCaptureError("URL is outside the exact public-source allowlist")
    request = Request(url, headers={
        "User-Agent": "decision-kernel-public-source-study/1.0",
        "Accept": "text/html,application/xhtml+xml", "Accept-Encoding": "identity",
    })
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    with opener.open(request, timeout=20) as response:
        headers = _safe_headers(dict(response.headers.items()))
        length = headers.get("content-length")
        if length is not None and (not re.fullmatch(r"[0-9]+", length) or int(length) > MAX_BODY_BYTES):
            raise EconomicCaptureError("response exceeds the declared byte budget")
        body = response.read(MAX_BODY_BYTES + 1)
        _body_integrity(body, headers)
        return PublicResponse(response.geturl(), response.status, headers, body)


class _VisibleText(HTMLParser):
    """Deterministic text projection, not a browser visibility/authenticity claim."""
    BLOCKS = {"p", "div", "br", "h1", "h2", "h3", "li", "tr", "section", "article", "header", "footer"}
    IGNORE = {"script", "style", "noscript", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.IGNORE:
            self.ignored.append(tag)
        if not self.ignored and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.ignored:
            if tag == self.ignored[-1]:
                self.ignored.pop()
            return
        if tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(re.sub(r"\s+", " ", data))


def decode_page(response: PublicResponse) -> str:
    if type(response.status) is not int or response.status != 200:
        raise EconomicCaptureError("response is not HTTP 200")
    headers = _safe_headers(response.headers)
    _body_integrity(response.body, headers)
    if headers.get("content-encoding", "identity").lower() not in {"", "identity"}:
        raise EconomicCaptureError("compressed response requires a separately reviewed decoder")
    message = Message()
    message["content-type"] = headers.get("content-type", "")
    if message.get_content_type() not in {"text/html", "application/xhtml+xml"}:
        raise EconomicCaptureError("response is not an HTML document")
    encodings = []
    if message.get_content_charset():
        encodings.append(message.get_content_charset())
    # Inspect charset declarations only inside meta elements, not arbitrary prose.
    for tag in re.findall(br"<meta\b[^>]*>", response.body[:16384], flags=re.I):
        match = re.search(br"charset\s*=\s*['\"]?\s*([a-zA-Z0-9_-]+)", tag, flags=re.I)
        if match:
            encodings.append(match[1].decode("ascii"))
    try:
        names = {codecs.lookup(name).name for name in encodings}
    except LookupError as exc:
        raise EconomicCaptureError("unknown declared HTML encoding") from exc
    if len(names) > 1 or (names and not names <= {"utf-8", "gbk", "gb2312"}):
        raise EconomicCaptureError("conflicting or unsupported declared HTML encoding")
    encoding = next(iter(names), "utf-8")
    # Undeclared bytes must be valid UTF-8; never decode with replacement characters.
    try:
        decoded = response.body.decode(encoding).lstrip("\ufeff")
    except UnicodeError as exc:
        raise EconomicCaptureError("HTML decoding failed") from exc
    parser = _VisibleText()
    parser.feed(decoded)
    parser.close()
    if parser.ignored:
        raise EconomicCaptureError("unterminated ignored HTML element")
    return "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip()) + "\n"


def bind_reviewed_source(source: Mapping[str, str], response: PublicResponse, *, captured_at: datetime):
    """Verify reviewed phrases against archived text; do not invent new releases.

    Binding is whitespace-normalized substring matching, not an exhaustive audit
    of every page claim. The full raw body is retained to inspect any added context.
    """
    qualify_release_excerpt(source)
    captured_at = _clock(captured_at)
    prior_capture = datetime.fromisoformat(source["captured_at"].replace("Z", "+00:00"))
    if captured_at < prior_capture:
        raise EconomicCaptureError("capture precedes the reviewed source record")
    if response.url != source["source_url"]:
        raise EconomicCaptureError("response identity differs from the exact reviewed URL")
    page = decode_page(response)
    compact = "".join(page.split())
    fragments = [("title", source["title"]), ("published_date", source["published_date"])]
    for index, line in enumerate(source["excerpt"].splitlines()):
        if not line.strip() or line.strip() == source["title"] or re.fullmatch(r"日期[：:]\s*" + re.escape(source["published_date"]), line.strip()):
            continue
        fragments.append((f"reviewed_line_{index}", line))
    matches = []
    for label, fragment in fragments:
        expected = "".join(fragment.split())
        position = compact.find(expected)
        if position < 0:
            raise EconomicCaptureError(f"reviewed fragment absent from captured page: {label}")
        matches.append({"label": label, "start": position, "end": position + len(expected)})
    if len(matches) < 3 or not matches[0]["start"] <= matches[1]["start"] < min(item["start"] for item in matches[2:]):
        raise EconomicCaptureError("publication date is not between the title and reviewed facts")
    rebound = dict(source)
    rebound["captured_at"] = captured_at.isoformat()
    observation = qualify_release_excerpt(rebound)
    binding = {
        "schema_version": 1, "semantics": "REVIEWED_EXCERPT_BOUND_TO_CAPTURE_NOT_AUTOMATIC_NEW_FACT_DISCOVERY",
        "reviewed_source_hash": canonical_hash(dict(source)), "raw_body_sha256": _sha(response.body),
        "normalized_text_sha256": _sha(compact.encode("utf-8")), "matches": matches,
        "captured_at": captured_at, "observation_hash": observation["observation_hash"], **AUTHORITY,
    }
    binding["binding_hash"] = canonical_hash(binding)
    return page, json.loads(canonical_json(binding)), observation


def _new_directory(root: Path) -> None:
    if root.exists() or any(path.is_symlink() for path in (root, *root.parents)):
        raise EconomicCaptureError("capture requires a new directory with no symlink ancestors")
    if "decision-state" in root.resolve().parts:
        raise EconomicCaptureError("economic captures cannot enter market-state storage")
    root.mkdir(parents=True, exist_ok=False)


def capture_reviewed_sources(sources: Sequence[Mapping[str, str]], root: Path, *,
                             transport: Callable[[str], PublicResponse] | None = None,
                             provenance: str = LIVE, now: Callable[[], datetime] | None = None) -> dict:
    if provenance not in {LIVE, SYNTHETIC} or ((transport is not None) != (provenance == SYNTHETIC)):
        raise EconomicCaptureError("injected transports must declare synthetic provenance and synthetic runs require an injected transport")
    if not 1 <= len(sources) <= MAX_SOURCES or len({source["source_url"] for source in sources}) != len(sources):
        raise EconomicCaptureError("source list must contain 1–4 unique reviewed pages")
    source_records = []
    for source in sources:
        qualify_release_excerpt(source)
        if provenance == LIVE and source["capture_method"] != "REVIEWED_OFFICIAL_WEB_EXCERPT":
            raise EconomicCaptureError("synthetic source cannot enter a public capture")
        source_records.append({**source, "capture_method": SYNTHETIC} if provenance == SYNTHETIC else dict(source))
    _new_directory(root)
    now = now or (lambda: datetime.now(timezone.utc))
    transport = transport or fetch_public_page
    manifest = {"schema_version": 1, "semantics": SEMANTICS, "provenance": provenance,
                "implementation": _implementation(), "status": "RECORDING", "records": [], "files": {}, **AUTHORITY}

    def flush():
        temporary = root / "manifest.tmp"
        temporary.write_bytes(_bytes({**manifest, "capture_hash": canonical_hash(manifest)}))
        temporary.replace(root / "manifest.json")

    def put(name: str, data: bytes):
        if len(data) > MAX_BODY_BYTES or sum(item["bytes"] for item in manifest["files"].values()) + len(data) > MAX_ARCHIVE_BYTES:
            raise EconomicCaptureError("capture storage budget exceeded")
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
        manifest["files"][name] = {"bytes": len(data), "sha256": _sha(data)}

    flush()
    for index, source in enumerate(source_records):
        prefix = f"{index:04d}"
        put(f"{prefix}/source.json", _bytes(source))
        record = {"index": index, "source_url": source["source_url"], "started_at": _clock(now()).isoformat(),
                  "completed_at": None, "status": "SOURCE_UNAVAILABLE", "error_type": None, "error_reason": None}
        try:
            response = transport(source["source_url"])
            record["completed_at"] = _clock(now()).isoformat()
            if datetime.fromisoformat(record["completed_at"]) < datetime.fromisoformat(record["started_at"]):
                raise EconomicCaptureError("capture completion clock precedes request")
            if not isinstance(response.body, bytes) or len(response.body) > MAX_BODY_BYTES:
                raise EconomicCaptureError("response body exceeds capture budget")
            metadata = {"url": response.url, "status": response.status, "headers": _safe_headers(response.headers)}
            put(f"{prefix}/response.bin", response.body)
            put(f"{prefix}/response.json", _bytes(metadata))
        except (OSError, ValueError, RuntimeError) as exc:
            record["completed_at"] = record["completed_at"] or _clock(now()).isoformat()
            record["error_type"] = type(exc).__name__
            record["error_reason"] = str(exc) if isinstance(exc, EconomicCaptureError) else "source transport failed; no retry or fallback"
        else:
            try:
                page, binding, observation = bind_reviewed_source(source, response,
                    captured_at=datetime.fromisoformat(record["completed_at"]))
            except (ValueError, RuntimeError) as exc:
                record.update(status="REJECTED_BINDING", error_type=type(exc).__name__,
                    error_reason=str(exc) if isinstance(exc, EconomicCaptureError) else "source qualification failed")
            else:
                put(f"{prefix}/page.txt", page.encode("utf-8"))
                put(f"{prefix}/binding.json", _bytes(binding))
                put(f"{prefix}/observation.json", _bytes(observation))
                record["status"] = MATCHED
        manifest["records"].append(record)
        flush()
    matched = sum(item["status"] == MATCHED for item in manifest["records"])
    manifest["status"] = "COMPLETE" if matched == len(sources) else "INCOMPLETE"
    summary = (f"## Official economic-source capture — {manifest['status']}\n\n"
               f"Reviewed excerpts bound to full captured pages: {matched}/{len(sources)}.\n\n"
               f"Provenance: {provenance}. Each selected URL was attempted once; no automatic retries.\n\n"
               "This is source capture and excerpt reconciliation, not a current industry signal, continuous feed, historical first-vintage proof, or company-profit conclusion.\n\n"
               "Raw HTML is retained as response.bin; do not execute it. Source records, response metadata and binding hashes are in the archive.\n\n"
               "HUMAN ATTENTION AUTHORITY = NONE; INVESTMENT AUTHORITY = NONE.\n")
    put("summary.md", summary.encode("utf-8"))
    flush()
    return {**manifest, "capture_hash": canonical_hash(manifest)}


def verify_capture(root: Path) -> dict:
    """Verify a trusted extracted archive without network or production writes."""
    if any(path.is_symlink() for path in (root, *root.parents)) or (root / "manifest.json").is_symlink():
        raise EconomicCaptureError("capture path must not be a symlink")
    if (root / "manifest.json").stat().st_size > 65536:
        raise EconomicCaptureError("manifest is oversized")
    payload = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    claimed = payload.pop("capture_hash")
    expected_fields = {"schema_version", "semantics", "provenance", "implementation", "status", "records", "files", *AUTHORITY}
    if set(payload) != expected_fields or claimed != canonical_hash(payload):
        raise EconomicCaptureError("capture manifest fields/hash disagree")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1 or payload["semantics"] != SEMANTICS or payload["provenance"] not in {LIVE, SYNTHETIC}:
        raise EconomicCaptureError("unsupported capture contract")
    if payload["implementation"] != _implementation() or any(payload[key] != value for key, value in AUTHORITY.items()):
        raise EconomicCaptureError("capture implementation or authority differs")
    records = payload["records"]
    if not 1 <= len(records) <= MAX_SOURCES or payload["status"] not in {"COMPLETE", "INCOMPLETE"}:
        raise EconomicCaptureError("capture is incomplete or has invalid cardinality")
    expected = {"manifest.json", *payload["files"]}
    actual = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise EconomicCaptureError("capture inventory contains a symlink")
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    if actual != expected or "summary.md" not in expected or sum(item["bytes"] for item in payload["files"].values()) > MAX_ARCHIVE_BYTES:
        raise EconomicCaptureError("capture inventory or byte budget disagrees")
    for name, entry in payload["files"].items():
        if name != "summary.md":
            parts = name.split("/")
            if len(parts) != 2 or parts[0] not in {f"{i:04d}" for i in range(len(records))} or parts[1] not in FILES:
                raise EconomicCaptureError("capture file path is outside the fixed inventory")
        path = root / name
        if set(entry) != {"bytes", "sha256"} or type(entry["bytes"]) is not int or path.stat().st_size > MAX_BODY_BYTES or path.stat().st_size != entry["bytes"] or _sha(path.read_bytes()) != entry["sha256"]:
            raise EconomicCaptureError("captured file hash or size disagrees")
    matched = 0
    seen_urls = set()
    for index, record in enumerate(records):
        prefix = f"{index:04d}"
        if set(record) != {"index", "source_url", "started_at", "completed_at", "status", "error_type", "error_reason"} or type(record["index"]) is not int or record["index"] != index:
            raise EconomicCaptureError("capture record fields or order differ")
        source = json.loads((root / prefix / "source.json").read_text(encoding="utf-8"))
        qualify_release_excerpt(source)
        if record["source_url"] != source["source_url"] or record["source_url"] in seen_urls:
            raise EconomicCaptureError("capture source identity differs or is repeated")
        seen_urls.add(record["source_url"])
        if (source["capture_method"] == SYNTHETIC) != (payload["provenance"] == SYNTHETIC):
            raise EconomicCaptureError("synthetic/public provenance differs")
        start = _clock(datetime.fromisoformat(record["started_at"]))
        end = _clock(datetime.fromisoformat(record["completed_at"]))
        if end < start:
            raise EconomicCaptureError("capture clocks are reversed")
        response = None
        if (root / prefix / "response.json").exists():
            metadata = json.loads((root / prefix / "response.json").read_text(encoding="utf-8"))
            if set(metadata) != {"url", "status", "headers"} or metadata["headers"] != _safe_headers(metadata["headers"]):
                raise EconomicCaptureError("response metadata fields differ")
            response = PublicResponse(metadata["url"], metadata["status"], metadata["headers"], (root / prefix / "response.bin").read_bytes())
        if record["status"] == MATCHED:
            if response is None or record["error_type"] is not None or record["error_reason"] is not None:
                raise EconomicCaptureError("successful capture lacks a response or carries an error")
            page, binding, observation = bind_reviewed_source(source, response, captured_at=end)
            for name, value in (("page.txt", page.encode("utf-8")), ("binding.json", _bytes(binding)), ("observation.json", _bytes(observation))):
                if (root / prefix / name).read_bytes() != value:
                    raise EconomicCaptureError("captured binding/output does not reconstruct from raw response")
            matched += 1
        elif record["status"] in {"SOURCE_UNAVAILABLE", "REJECTED_BINDING"}:
            if any((root / prefix / name).exists() for name in ("page.txt", "binding.json", "observation.json")) or not record["error_type"] or not record["error_reason"]:
                raise EconomicCaptureError("rejected capture cannot carry a successful observation or omit its error")
            if record["status"] == "REJECTED_BINDING":
                if response is None:
                    raise EconomicCaptureError("rejected binding lacks its response")
                try:
                    bind_reviewed_source(source, response, captured_at=end)
                except (ValueError, RuntimeError) as exc:
                    reason = str(exc) if isinstance(exc, EconomicCaptureError) else "source qualification failed"
                    if record["error_type"] != type(exc).__name__ or record["error_reason"] != reason:
                        raise EconomicCaptureError("recorded rejection differs from raw reconstruction") from exc
                else:
                    raise EconomicCaptureError("recorded rejection now accepts its retained response")
        else:
            raise EconomicCaptureError("unsupported capture disposition")
    if (payload["status"] == "COMPLETE") != (matched == len(records)):
        raise EconomicCaptureError("aggregate capture status disagrees")
    return {"capture_hash": claimed, "archive_integrity": "VERIFIED", "matched_excerpts": matched,
            "attempted_sources": len(records), "status": payload["status"], "network_calls": 0,
            "production_state_writes": 0, "semantics": "OFFLINE_CAPTURE_VERIFICATION_NOT_PROVIDER_AUTHENTICATION", **AUTHORITY}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Bounded public-source archival, no market-state or event writer.")
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("capture")
    capture.add_argument("sources", type=Path)
    capture.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("archive", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "capture":
            if args.sources.stat().st_size > 256 * 1024 or args.sources.resolve().is_relative_to(args.output.resolve()):
                raise EconomicCaptureError("source list is oversized or inside output")
            sources = json.loads(args.sources.read_text(encoding="utf-8"))
            if not isinstance(sources, list):
                raise EconomicCaptureError("source list must be a JSON array")
            report = capture_reviewed_sources(sources, args.output)
            print(f"Economic source capture: {report['status']}; sources={len(report['records'])}; capture_hash={report['capture_hash']}")
        else:
            report = verify_capture(args.archive)
            print(canonical_json(report))
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        parser.exit(2, f"Economic capture unavailable: {type(exc).__name__}\n")
    return 0 if report["status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
