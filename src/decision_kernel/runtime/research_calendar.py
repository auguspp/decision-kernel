"""Bounded BLS schedule reading, not a source collector or a task scheduler.

Consumes a reviewed TEXT EXCERPT of three selected BLS monthly releases. It
cannot authenticate a website, acquire release contents, infer holdings, or
establish that a scheduled event actually happened. See docs/research-calendar-v1.md.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, time, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from decision_kernel.identity import canonical_hash, canonical_json

VERSION = "bls-research-calendar-v1"
SOURCE_ZONE = "America/New_York"
MAX_SOURCE_BYTES = 64 * 1024
MAX_SAVED_BYTES = 256 * 1024
FILES = {"source.txt", "request.json", "calendar.json", "calendar.md"}
MONTHS = ("January February March April May June July August September October "
          "November December").split()
WEEKDAYS = "Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split()
SERIES = {
    "Employment Situation": ("employment", "美国就业报告"),
    "Consumer Price Index": ("cpi", "美国消费者价格指数"),
    "Producer Price Index": ("ppi", "美国生产者价格指数"),
}
MONTH = "(?:" + "|".join(MONTHS) + ")"
DAY = rf"(?P<month>{MONTH}) (?P<day>[0-9]{{1,2}}), (?P<year>[0-9]{{4}})"
ROW = re.compile(
    rf"(?P<weekday>{'|'.join(WEEKDAYS)}), {DAY} "
    rf"(?:(?P<clock>[0-9]{{2}}:[0-9]{{2}} [AP]M) )?"
    rf"(?P<series>{'|'.join(SERIES)}) for "
    rf"(?P<period_month>{MONTH}) (?P<period_year>[0-9]{{4}})"
)
URL = re.compile(r"https://www\.bls\.gov/schedule/([0-9]{4})/([0-9]{2})_sched_list\.htm")
NOTE = "NOTE: All times on calendar are Eastern Time."
REQUEST_KEYS = {"source_url", "reviewed_at", "as_of", "window_start", "window_end",
                "local_timezone", "observation_kind"}


class CalendarError(ValueError):
    """A bounded calendar input or its retained representation was rejected."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise CalendarError(reason)


def _day(value: str) -> date:
    _require(isinstance(value, str) and bool(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value)),
             "DATE_FORMAT")
    return date.fromisoformat(value)


def _clock(value: str) -> datetime:
    _require(isinstance(value, str) and len(value) <= 40, "CLOCK_FORMAT")
    result = datetime.fromisoformat(value)
    _require(result.tzinfo is not None and result.utcoffset() is not None, "CLOCK_TIMEZONE")
    return result


def _encoded(value: dict) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def _english_day(value: str) -> date:
    match = re.fullmatch(DAY, value)
    _require(match is not None, "SOURCE_DATE_FORMAT")
    return date(int(match["year"]), MONTHS.index(match["month"]) + 1, int(match["day"]))


def _scheduled(day: date, clock: str | None) -> datetime | None:
    if clock is None:
        return None  # A date-only appointment is not midnight in either zone.
    hour, minute = int(clock[:2]), int(clock[3:5])
    _require(1 <= hour <= 12 and 0 <= minute <= 59, "SOURCE_TIME_FORMAT")
    wall = datetime.combine(day, time(hour % 12 + (12 if clock[-2:] == "PM" else 0), minute))
    aware = wall.replace(tzinfo=ZoneInfo(SOURCE_ZONE))
    _require(aware.utcoffset() == aware.replace(fold=1).utcoffset()
             and aware.astimezone(timezone.utc).astimezone(aware.tzinfo).replace(tzinfo=None) == wall,
             "AMBIGUOUS_OR_NONEXISTENT_SOURCE_TIME")
    return aware


def build_calendar(source: bytes, *, source_url: str, reviewed_at: str, as_of: str,
                   window_start: str, window_end: str,
                   local_timezone: str = "Asia/Singapore",
                   observation_kind: str = "REVIEWED_WEB_EXCERPT") -> dict:
    """Parse only explicitly retained rows; the window uses ORIGINAL source dates.

    reviewed_at is the recorded review clock, not a fabricated HTTP request clock.
    Caller-supplied provenance is an assertion; consistency checks do not certify it.
    """
    _require(isinstance(source, bytes) and 0 < len(source) <= MAX_SOURCE_BYTES, "SOURCE_BYTES")
    text = source.decode("utf-8")
    _require(not any(ord(c) < 32 and c not in "\n\r\t" for c in text), "SOURCE_CONTROL_CHARACTER")
    match = URL.fullmatch(source_url) if isinstance(source_url, str) else None
    _require(match is not None, "SOURCE_URL")
    year, month = map(int, match.groups())
    date(year, month, 1)
    _require(observation_kind in {"REVIEWED_WEB_EXCERPT", "SYNTHETIC_TEST_ONLY"}, "OBSERVATION_KIND")
    reviewed, cutoff = _clock(reviewed_at), _clock(as_of)
    _require(reviewed <= cutoff, "REVIEW_AFTER_AS_OF")
    start, end = _day(window_start), _day(window_end)
    _require(0 <= (end - start).days < 42, "WINDOW_MUST_BE_1_TO_42_DAYS")
    _require(isinstance(local_timezone, str), "LOCAL_TIMEZONE")
    local = ZoneInfo(local_timezone)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    _require(any(line.lstrip("# ") == f"{MONTHS[month - 1]} {year}" for line in lines),
             "SOURCE_MONTH_HEADING")
    notes = [line for line in lines if line.startswith("NOTE: All times on calendar")]
    _require(len(notes) == 1 and (notes[0] == NOTE or notes[0].startswith(NOTE + "Last Modified Date:")
                                or notes[0].startswith(NOTE + " Last Modified Date:")),
             "SOURCE_TIMEZONE_STATEMENT")
    modified = "UNKNOWN"
    modifications = re.findall(rf"Last Modified Date: ({MONTH} [0-9]{{1,2}}, [0-9]{{4}})", text)
    _require(len(modifications) <= 1, "AMBIGUOUS_MODIFIED_DATE")
    if modifications:
        modified_day = _english_day(modifications[0])
        _require(modified_day <= reviewed.astimezone(ZoneInfo(SOURCE_ZONE)).date(), "FUTURE_MODIFIED_DATE")
        modified = modified_day.isoformat()
    digest = sha256(source).hexdigest()
    events, seen, parsed = [], set(), 0
    for number, line in enumerate(lines, 1):
        if not any(name in line for name in SERIES):
            continue
        row = ROW.fullmatch(line)
        _require(row is not None, "MALFORMED_SELECTED_SOURCE_ROW")
        scheduled_day = _english_day(f'{row["month"]} {row["day"]}, {row["year"]}')
        _require((scheduled_day.year, scheduled_day.month) == (year, month), "ROW_SOURCE_MONTH_MISMATCH")
        _require(WEEKDAYS[scheduled_day.weekday()] == row["weekday"], "SOURCE_WEEKDAY_MISMATCH")
        period = date(int(row["period_year"]), MONTHS.index(row["period_month"]) + 1, 1)
        _require(period <= scheduled_day, "REPORTING_PERIOD_AFTER_SCHEDULE")
        code, title = SERIES[row["series"]]
        identity = f"BLS:{code}:{period:%Y-%m}"
        _require(identity not in seen, "DUPLICATE_OR_CONFLICTING_EVENT")
        seen.add(identity)
        parsed += 1
        _require(parsed <= 64, "ROW_BUDGET")
        instant = _scheduled(scheduled_day, row["clock"])
        if not start <= scheduled_day <= end:
            continue
        events.append({
            "event_id": identity, "title": title, "source_series": row["series"],
            "reporting_period": period.strftime("%Y-%m"), "date_status": "SCHEDULED",
            "scheduled_date": scheduled_day.isoformat(), "source_timezone": SOURCE_ZONE,
            "time_precision": "MINUTE" if instant else "DATE_ONLY",
            "scheduled_at": instant.isoformat() if instant else "UNKNOWN",
            "local_scheduled_at": instant.astimezone(local).isoformat() if instant else "UNKNOWN",
            "actual_release_at": "UNKNOWN", "release_observed": "NOT_CHECKED",
            "release_material_obtained": "NOT_CHECKED", "analysis": "NOT_RUN",
            "human_response": "NOT_RECORDED", "source_line": number, "source_sha256": digest,
        })
    _require(parsed > 0, "NO_SELECTED_SOURCE_ROWS")
    events.sort(key=lambda event: (event["scheduled_date"], event["scheduled_at"], event["event_id"]))
    result = {
        "version": VERSION, "as_of": as_of,
        "status": "SCHEDULED_EVENTS_IN_WINDOW" if events else "NO_SELECTED_EVENTS_IN_WINDOW",
        "coverage": "THREE_BLS_SERIES_IN_REVIEWED_EXCERPT_NOT_COMPLETE_CALENDAR",
        "company_events": "NOT_IMPLEMENTED_NO_FOLLOW_OR_HOLDING_INFERENCE",
        "window": {"start": window_start, "end": window_end, "basis": "SOURCE_DATE", "timezone": SOURCE_ZONE},
        "local_timezone": local_timezone,
        "source": {"url": source_url, "reviewed_at": reviewed_at, "observation_kind": observation_kind,
                   "retrieved_at": "UNKNOWN", "published_at": "UNKNOWN", "last_modified_date": modified,
                   "path": "source.txt", "bytes": len(source), "sha256": digest,
                   "custody": "EXCERPT_BYTES_ONLY_NOT_ORIGINAL_HTTP_BODY"},
        "parsed_rows": parsed, "excluded_outside_window": parsed - len(events), "events": events,
        "authority": {"research": "NONE", "human_attention": "NONE", "investment": "NONE", "execution": "NONE"},
    }
    result["calendar_hash"] = canonical_hash(result)
    return result


def render_calendar(calendar: dict) -> str:
    """Render derived text only after checking the bundle's content hash."""
    _require(isinstance(calendar, dict) and calendar.get("version") == VERSION, "CALENDAR_VERSION")
    _require(calendar.get("calendar_hash") == canonical_hash(
        {key: value for key, value in calendar.items() if key != "calendar_hash"}), "CALENDAR_HASH")
    lines = ["# 有限近期宏观研究日历", "",
             "仅为官方日历核读摘录中的预约，不证明发布、取得材料、分析或 Human 回应。",
             f"范围：{calendar['window']['start']} 至 {calendar['window']['end']}（原时区 {SOURCE_ZONE} 的日期）；"
             f"本地展示：{calendar['local_timezone']}。",
             f"来源：{calendar['source']['url']}",
             f"核读时刻：{calendar['source']['reviewed_at']}；HTTP 取得/首发时刻：UNKNOWN。",
             "保管对象为摘录原字节，不是原始 HTTP 正文；覆盖仅限所选 BLS 三系列。", "",
             "| 事件 | 报告期 | 原时区预约 | 本地预约 | 状态 |",
             "|---|---|---|---|---|"]
    for event in calendar["events"]:
        original = event["scheduled_at"] if event["time_precision"] == "MINUTE" else event["scheduled_date"] + "（时间未知）"
        lines.append(f"| {event['title']} | {event['reporting_period']} | {original} | "
                     f"{event['local_scheduled_at']} | 预约；实际发布未检查 |")
    if not calendar["events"]:
        lines.append("\n此窗口内无所选摘录事件；不代表完整日历无事件或已经检查全部来源。")
    lines += ["", "公司事件/关注或持有身份未接入；日历不触发研究、提醒或投资执行。",
              f"摘录 SHA256：{calendar['source']['sha256']}",
              f"Calendar hash：{calendar['calendar_hash']}"]
    return "\n".join(lines) + "\n"


def _safe_path(path: Path) -> None:
    _require(not any(item.is_symlink() for item in (path, *path.parents)), "SYMLINK_REJECTED")


def save_calendar(output: Path, source: bytes, **request) -> dict:
    """Create a new immutable-by-convention bundle; never replace old snapshots."""
    output = Path(output)
    _safe_path(output)
    # Record every default so replay never depends on later CLI defaults.
    request = {"local_timezone": "Asia/Singapore", "observation_kind": "REVIEWED_WEB_EXCERPT", **request}
    _require(set(request) == REQUEST_KEYS, "REQUEST_KEYS")
    calendar = build_calendar(source, **request)
    bodies = {"source.txt": source, "request.json": _encoded(request),
              "calendar.json": _encoded(calendar), "calendar.md": render_calendar(calendar).encode("utf-8")}
    _require(all(len(body) <= MAX_SAVED_BYTES for body in bodies.values()), "SAVED_BYTE_BUDGET")
    output.mkdir(parents=True, exist_ok=False)
    # A partial I/O failure remains an incomplete bundle, not a successful save.
    for name, body in bodies.items():
        with (output / name).open("xb") as stream:
            stream.write(body)
    return read_calendar(output, expected_hash=calendar["calendar_hash"])


def read_calendar(folder: Path, *, expected_hash: str | None = None) -> dict:
    """Reparse retained bytes and compare BOTH outputs. No HTTP or state writes.

    Without an externally supplied expected hash this proves internal consistency,
    not authenticity against coordinated replacement of an entire directory.
    """
    folder = Path(folder)
    _safe_path(folder)
    _require(folder.is_dir() and {p.name for p in folder.iterdir()} == FILES, "BUNDLE_INVENTORY")
    bodies = {}
    for name in FILES:
        path = folder / name
        _safe_path(path)
        _require(path.is_file(), "BUNDLE_FILE_TYPE")
        with path.open("rb") as stream:
            bodies[name] = stream.read(MAX_SAVED_BYTES + 1)
        _require(len(bodies[name]) <= MAX_SAVED_BYTES, "SAVED_BYTE_BUDGET")
    request = json.loads(bodies["request.json"])
    _require(isinstance(request, dict) and set(request) == REQUEST_KEYS, "REQUEST_KEYS")
    _require(_encoded(request) == bodies["request.json"], "REQUEST_BYTES")
    calendar = build_calendar(bodies["source.txt"], **request)
    _require(_encoded(calendar) == bodies["calendar.json"], "CALENDAR_BYTES")
    _require(render_calendar(calendar).encode("utf-8") == bodies["calendar.md"], "MARKDOWN_BYTES")
    _require(expected_hash is None or calendar["calendar_hash"] == expected_hash, "EXPECTED_HASH")
    return calendar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="Save a bounded reviewed BLS text excerpt; no network")
    build.add_argument("source", type=Path)
    build.add_argument("output", type=Path)
    for name in ("source-url", "reviewed-at", "as-of", "window-start", "window-end"):
        build.add_argument("--" + name, required=True)
    build.add_argument("--local-timezone", default="Asia/Singapore")
    build.add_argument("--synthetic", action="store_true")
    verify = commands.add_parser("verify", help="Read back retained bytes, optionally against an external hash")
    verify.add_argument("folder", type=Path)
    verify.add_argument("--expected-hash")
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    try:
        if command == "build":
            source_path, output = args.pop("source"), args.pop("output")
            _safe_path(source_path)
            with source_path.open("rb") as stream:
                source = stream.read(MAX_SOURCE_BYTES + 1)
            args["observation_kind"] = "SYNTHETIC_TEST_ONLY" if args.pop("synthetic") else "REVIEWED_WEB_EXCERPT"
            result = save_calendar(output, source, **args)
        else:
            result = read_calendar(args["folder"], expected_hash=args["expected_hash"])
        print(canonical_json({"calendar_hash": result["calendar_hash"], "events": len(result["events"]),
                              "status": result["status"]}))
        return 0
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.exit(2, f"Calendar rejected: {type(exc).__name__}\n")


if __name__ == "__main__":
    raise SystemExit(main())
