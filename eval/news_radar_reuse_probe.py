#!/usr/bin/env python3
"""Bounded external News Radar reuse probe.

Reads NewsNow and two optional RSSHub feeds once each. It retains public response
bytes and source clocks, normalizes article observations, and produces only
conservative event/topic candidates. No fact acceptance, sentiment/impact score,
Research routing, or investment authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

import feedparser
import requests

NEWSNOW = "https://newsnow.busiyi.world/api/s"
SOURCES = {
    "cls": ("cls.cn",),
    "wallstreetcn": ("wallstreetcn.com",),
    "fastbull": ("fastbull.com", "fastbull.cn"),
    "jin10": ("jin10.com",),
    "mktnews": ("mktnews.net",),
    "gelonghui": ("gelonghui.com",),
    "thepaper": ("thepaper.cn",),
}
RSS = {
    "rsshub-yicai": ("https://rsshub.app/yicai/latest", ("yicai.com",)),
    "rsshub-stcn-yw": ("https://rsshub.app/stcn/article/list/yw", ("stcn.com",)),
}
TOPICS = {
    "LITHIUM": ("碳酸锂", "锂矿", "锂电"),
    "COPPER": ("沪铜", "铜价", "铜矿", "精炼铜"),
    "BLACK_CHAIN": ("螺纹", "钢铁", "焦煤", "焦炭", "铁矿"),
}
MAX_BODY = 2 * 1024 * 1024
MAX_ITEMS = 30
AUTHORITY = {
    "human_attention_authority": "NONE",
    "research_authority": "NONE",
    "investment_authority": "NONE",
    "signal_transition_authority": "NONE",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def raw(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else raw(value))


def domain_ok(url: str, allowed: tuple[str, ...]) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and any(host == d or host.endswith("." + d) for d in allowed)


def parse_clock(value):
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            n = float(value)
            if n > 10_000_000_000:
                n /= 1000
            return datetime.fromtimestamp(n, tz=timezone.utc).isoformat()
        if isinstance(value, str):
            text = value.strip()
            if re.fullmatch(r"\d{10,13}", text):
                return parse_clock(int(text))
            try:
                dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
                if dt.tzinfo is not None:
                    return dt.astimezone(timezone.utc).isoformat()
            except ValueError:
                pass
            dt = parsedate_to_datetime(text)
            if dt.tzinfo is not None:
                return dt.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        return None
    return None


def title_key(title: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", title.lower())


def bigrams(text: str) -> set[str]:
    return {text[i:i+2] for i in range(max(0, len(text)-1))}


def likely_same_event(a: str, b: str) -> tuple[bool, str | None]:
    ka, kb = title_key(a), title_key(b)
    if not ka or not kb:
        return False, None
    if ka == kb:
        return True, "EXACT_NORMALIZED_TITLE"
    short, long = sorted((ka, kb), key=len)
    if len(short) >= 12 and short in long:
        return True, "LONG_TITLE_CONTAINS_SHORT_TITLE"
    ba, bb = bigrams(ka), bigrams(kb)
    if len(ba | bb) >= 8 and len(ba & bb) / len(ba | bb) >= 0.90:
        return True, "TITLE_BIGRAM_JACCARD_GE_0_90"
    return False, None


def topic_candidates(title: str):
    return [topic for topic, words in TOPICS.items() if any(w in title for w in words)]


def security_text_candidates(title: str):
    return sorted(set(re.findall(r"(?<!\d)(?:00|30|60|68)\d{4}(?!\d)", title)))


def capture(session: requests.Session, url: str, path: Path, *, label: str):
    requested_at = now()
    record = {"label": label, "url": url, "requested_at": requested_at, "received_at": None,
              "status": "FAILED", "http_status": None, "bytes": None, "sha256": None,
              "error_type": None}
    try:
        response = session.get(url, timeout=15, allow_redirects=True,
                               headers={"Accept": "application/json, application/rss+xml, application/xml, text/xml;q=0.9"})
        body = response.content
        record["received_at"] = now()
        record["http_status"] = response.status_code
        record["bytes"] = len(body)
        record["sha256"] = sha(body)
        if len(body) > MAX_BODY:
            record.update(status="SOURCE_UNAVAILABLE", error_type="BODY_OVER_BUDGET")
            return record, None
        write(path, body)
        if response.status_code != 200:
            record.update(status="SOURCE_UNAVAILABLE", error_type="HTTP_STATUS")
            return record, None
        record["status"] = "CAPTURED_PUBLIC_RESPONSE"
        return record, body
    except requests.RequestException as exc:
        record["received_at"] = now()
        record.update(status="SOURCE_UNAVAILABLE", error_type=type(exc).__name__)
        return record, None


def newsnow_rows(source_id: str, body: bytes, fetched_at: str):
    value = json.loads(body)
    if not isinstance(value, dict) or value.get("status") not in {"success", "cache"}:
        raise ValueError("NEWSNOW_RESPONSE_STATUS_UNSUPPORTED")
    items = value.get("items")
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        raise ValueError("NEWSNOW_ITEMS_OUTSIDE_BUDGET")
    allowed = SOURCES[source_id]
    rows = []
    for rank, item in enumerate(items, 1):
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        if not isinstance(title, str) or not title.strip():
            continue
        urls = [x for x in (item.get("url"), item.get("mobileUrl")) if isinstance(x, str) and x]
        if not urls or any(not domain_ok(u, allowed) for u in urls):
            raise ValueError("NEWSNOW_ITEM_DOMAIN_OR_SCHEME_MISMATCH")
        published = parse_clock(item.get("pubDate"))
        extra = item.get("extra")
        if published is None and isinstance(extra, dict):
            published = parse_clock(extra.get("date"))
        canonical = item.get("url") or item.get("mobileUrl")
        item_id = item.get("id")
        identity = sha(raw({"source": source_id, "id": item_id, "url": canonical, "title": title.strip()}))
        rows.append({
            "observation_id": identity,
            "source_kind": "NEWSNOW_EXTERNAL_SERVICE",
            "source_id": source_id,
            "returned_source_id": value.get("id"),
            "source_status": value.get("status"),
            "source_updated_at": parse_clock(value.get("updatedTime")),
            "source_item_id": str(item_id) if item_id is not None else None,
            "rank": rank,
            "title": title.strip(),
            "url": canonical,
            "published_at": published,
            "fetched_at": fetched_at,
            "security_text_candidates": security_text_candidates(title),
            "topic_keyword_candidates": topic_candidates(title),
            "article_fact_accepted": False,
            **AUTHORITY,
        })
    return rows


def rss_rows(source_id: str, body: bytes, fetched_at: str, allowed: tuple[str, ...]):
    parsed = feedparser.parse(body, sanitize_html=False, resolve_relative_uris=False)
    if parsed.get("bozo", 1) or parsed.get("version") not in {"rss20", "rss10", "atom10"}:
        raise ValueError("RSS_NOT_WELL_FORMED_SUPPORTED_FEED")
    entries = parsed.get("entries", [])
    if len(entries) > 100:
        raise ValueError("RSS_ITEMS_OUTSIDE_BUDGET")
    rows = []
    for rank, entry in enumerate(entries[:MAX_ITEMS], 1):
        title = entry.get("title")
        link = entry.get("link")
        if not isinstance(title, str) or not title.strip() or not isinstance(link, str) or not domain_ok(link, allowed):
            continue
        published = parse_clock(entry.get("published")) or parse_clock(entry.get("updated"))
        identity = sha(raw({"source": source_id, "id": entry.get("id"), "url": link, "title": title.strip()}))
        rows.append({
            "observation_id": identity,
            "source_kind": "RSSHUB_EXTERNAL_SERVICE",
            "source_id": source_id,
            "returned_source_id": source_id,
            "source_status": "feed",
            "source_updated_at": None,
            "source_item_id": str(entry.get("id")) if entry.get("id") is not None else None,
            "rank": rank,
            "title": title.strip(),
            "url": link,
            "published_at": published,
            "fetched_at": fetched_at,
            "security_text_candidates": security_text_candidates(title),
            "topic_keyword_candidates": topic_candidates(title),
            "article_fact_accepted": False,
            **AUTHORITY,
        })
    return rows


def cluster(rows: list[dict]):
    groups = []
    assigned = set()
    for i, row in enumerate(rows):
        if i in assigned:
            continue
        members, reasons = [i], []
        for j in range(i + 1, len(rows)):
            if j in assigned:
                continue
            same, reason = likely_same_event(row["title"], rows[j]["title"])
            if same:
                members.append(j)
                reasons.append({"left": row["observation_id"], "right": rows[j]["observation_id"], "rule": reason})
                assigned.add(j)
        assigned.add(i)
        if len(members) > 1:
            observations = [rows[k] for k in members]
            groups.append({
                "event_candidate_id": sha(raw(sorted(x["observation_id"] for x in observations))),
                "status": "POSSIBLE_SAME_EVENT_NOT_FACT_ACCEPTED",
                "members": [x["observation_id"] for x in observations],
                "sources": sorted(set(x["source_id"] for x in observations)),
                "rules": reasons,
                "representative_title": observations[0]["title"],
                **AUTHORITY,
            })
    return groups


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--newsnow-base-url", default=NEWSNOW)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    session = requests.Session()
    attempts, observations = [], []

    for source_id in SOURCES:
        url = f"{args.newsnow_base_url}?id={source_id}&latest"
        rec, body = capture(session, url, args.output / "raw" / f"newsnow-{source_id}.json", label=source_id)
        attempts.append(rec)
        if body is None:
            continue
        try:
            observations.extend(newsnow_rows(source_id, body, rec["received_at"]))
        except (ValueError, json.JSONDecodeError) as exc:
            rec.update(status="SOURCE_UNAVAILABLE", error_type=type(exc).__name__, validation_reason=str(exc))
    for source_id, (url, allowed) in RSS.items():
        rec, body = capture(session, url, args.output / "raw" / f"{source_id}.xml", label=source_id)
        attempts.append(rec)
        if body is None:
            continue
        try:
            observations.extend(rss_rows(source_id, body, rec["received_at"], allowed))
        except ValueError as exc:
            rec.update(status="SOURCE_UNAVAILABLE", error_type=type(exc).__name__, validation_reason=str(exc))

    event_candidates = cluster(observations)
    unique_urls = len({x["url"] for x in observations})
    summary = {
        "schema_version": 1,
        "semantics": "EXTERNAL_NEWS_OBSERVATION_PROBE_NOT_EVIDENCE_OR_RESEARCH",
        "generated_at": now(),
        "newsnow_upstream": "newsnext/newsnow@0f95b2c998dffbfd2ddbc51b47b5809887dc6b97",
        "newsnow_base_url": args.newsnow_base_url,
        "trendradar_prior_art": "sansan0/TrendRadar@792bcc3928b1617bba09df34989fd5675c159b86",
        "requests": len(attempts),
        "source_successes": sum(x["status"] == "CAPTURED_PUBLIC_RESPONSE" for x in attempts),
        "source_failures": sum(x["status"] != "CAPTURED_PUBLIC_RESPONSE" for x in attempts),
        "observations": len(observations),
        "unique_urls": unique_urls,
        "duplicate_url_observations": len(observations) - unique_urls,
        "possible_event_clusters": len(event_candidates),
        "observations_with_qualified_publish_clock": sum(x["published_at"] is not None for x in observations),
        "topic_candidate_counts": {k: sum(k in x["topic_keyword_candidates"] for x in observations) for k in TOPICS},
        "security_text_candidate_observations": sum(bool(x["security_text_candidates"]) for x in observations),
        "event_cluster_truth_accepted": False,
        **AUTHORITY,
    }
    write(args.output / "attempts.json", attempts)
    write(args.output / "news-observations.json", observations)
    write(args.output / "event-candidates.json", event_candidates)
    write(args.output / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
