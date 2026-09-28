"""Read an explicit calendar and optional predecessor through existing Git custody.

No discovery, network provider, new state store or event-state transition. The
original v1 parser/replay owns date semantics; this adapter owns registration.
"""
from __future__ import annotations

from pathlib import Path
import re
from tempfile import TemporaryDirectory

from . import current_state as model
from . import current_state_delivery as delivery
from . import research_calendar as calendar

VERSION = "research-calendar-reading-v1"
STATUS = "SAVED_REVIEWED_CALENDAR"
MEANING = "SAVED_APPOINTMENTS_NOT_RELEASE_OR_RESEARCH"


def _read_snapshot(collector, config, *, reserved_paths=()) -> dict:
    """A local gap never promotes partial bytes or silently substitutes an old R."""
    result = {"version": VERSION, "meaning": MEANING, **model.AUTHORITY}
    if config is None:
        return {**result, "status": "NOT_CONFIGURED"}
    files_before, sources_before = collector.files, collector.sources
    stage = "REGISTRATION"
    try:
        model.check(isinstance(config, dict) and set(config) ==
                    {"ref", "directory", "calendar_hash", "blobs"}, "calendar registration fields")
        ref, directory, expected = config["ref"], config["directory"], config["calendar_hash"]
        model.check(isinstance(ref, str) and model.SHA.fullmatch(ref), "calendar source commit")
        model.safe_path(directory)
        model.check(directory.startswith("docs/readings/") and
                    re.fullmatch(r"[A-Za-z0-9_./-]+", directory), "calendar source directory")
        model.check(isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected), "calendar external hash")
        blobs = config["blobs"]
        model.check(isinstance(blobs, dict) and set(blobs) == calendar.FILES and
                    all(isinstance(b, str) and model.SHA.fullmatch(b) for b in blobs.values()),
                    "calendar complete registered inventory")
        # Four explicit files get their own bounded source-cache scope, as in the
        # existing optional readers. Do not enlarge or consume the baseline's 60
        # source slots, change the real API counter, or borrow a new API allowance.
        stage = "CAPACITY"
        used = getattr(collector.api, "calls", None)
        model.check(type(used) is int and used >= 0, "calendar API accounting")
        paths = {"sources/git/" + blobs[name] + "/" + name for name in calendar.FILES}
        pending = len(set(files_before) | paths | set(reserved_paths) | {"current-state.json", "README.md"})
        model.check(used + len(calendar.FILES) + pending + 5 <= delivery.MAX_API_CALLS,
                    "calendar publication reserve")
        collector.files = dict(files_before)
        collector.sources = {key: value for key, value in sources_before.items()
                             if key in {(directory + "/" + name, ref) for name in calendar.FILES}}
        references = {}
        stage = "SOURCE"
        with TemporaryDirectory(prefix="kernel-calendar-reading-") as tmp:
            folder = Path(tmp)
            for name in sorted(calendar.FILES):
                raw, source = collector.source({"path": directory + "/" + name,
                                                 "ref": ref, "git_blob": blobs[name]})
                model.check(isinstance(raw, bytes) and len(raw) <= calendar.MAX_SAVED_BYTES and
                            model.blob_sha(raw) == blobs[name], "calendar source bytes")
                # Independently bind returned descriptors, not just the caller's spec.
                model.check(source["repository"] == model.REPOSITORY and source["ref"] == ref and
                            source["path"] == directory + "/" + name and source["git_blob"] == blobs[name] and
                            source["bytes"] == len(raw) and source["sha256"] == model.sha256(raw) and
                            source["read_ref_rule"] == "USE_THE_SAME_PINNED_READING_COMMIT" and
                            source["read_path"] == "sources/git/" + blobs[name] + "/" + name,
                            "calendar source descriptor")
                (folder / name).write_bytes(raw)
                references[name] = source
            stage = "REPLAY"
            saved = calendar.read_calendar(folder, expected_hash=expected)
        stage = "OBSERVATION"
        model.check(saved["source"]["observation_kind"] == "REVIEWED_WEB_EXCERPT",
                    "synthetic calendar is not a published observation")
        checked = collector.now()
        model.check(model.clock(saved["as_of"]) <= model.clock(checked), "calendar check precedes source review")
        return {**result, "status": STATUS, "checked_at": checked, "as_of": saved["as_of"],
                "source_commit": ref, "calendar_hash": expected, "files": references,
                "coverage": saved["coverage"], "window": saved["window"],
                "event_count": len(saved["events"]), "company_events": saved["company_events"]}
    except (ValueError, KeyError, TypeError, AttributeError, OSError, RuntimeError) as exc:
        collector.files = files_before
        # Only allowlisted local labels; never publish arbitrary exception text.
        codes = {"calendar API accounting": "API_ACCOUNTING_UNAVAILABLE",
                 "calendar publication reserve": "PUBLICATION_RESERVE",
                 "source registry bound": "SOURCE_FILE_BUDGET",
                 "reading retention batch limit": "RETENTION_BYTE_BUDGET",
                 "registered frozen blob changed": "SOURCE_BLOB_MISMATCH"}
        message = exc.args[0] if isinstance(exc, ValueError) and len(exc.args) == 1 else None
        code = codes.get(message, "UNCLASSIFIED_READ_REJECTION") if type(message) is str else "UNCLASSIFIED_READ_REJECTION"
        return {**result, "status": "UNAVAILABLE_OR_REJECTED", "error_type": type(exc).__name__,
                "diagnostic": {"stage": stage, "code": code,
                               "baseline_source_count": len(sources_before)},
                "limitation": "CALENDAR_READ_GAP_NOT_NO_EVENTS_OR_CANCELLATION"}

    finally:
        # Accepted bytes stay in the one reading inventory. The baseline cache is
        # restored even on failure; real API requests are never rolled back.
        collector.sources = sources_before


COMPARISON_STATUS = "SAVED_EXPLICIT_PREDECESSOR_COMPARISON"
COMPARISON_PATHS = {"json": "details/research/calendar-comparison.json",
                    "markdown": "details/research/calendar-comparison.md"}


def _comparison_markdown(report: dict, previous: dict, current: dict) -> bytes:
    """Render the original comparison's validated values, never new event semantics."""
    labels = {"UNCHANGED_SCHEDULE": "预约未变", "SOURCE_SCHEDULE_CHANGED": "来源预约字段变化",
              "TIME_PRECISION_CHANGED": "时间精度变化", "PREDECESSOR_ONLY": "仅前驱可见；非取消",
              "SUCCESSOR_ONLY": "仅当前可见；非首次公告"}
    lines = ["# 显式前驱日历比较", "",
             "调用者指定的双快照比较，不证明官方修订链、取消、实际发布或研究完成。",
             "覆盖仅限各自所选摘录与窗口；未见不代表取消，UNKNOWN 不当午夜。", ""]
    for side, title, snapshot in (("predecessor", "前驱", previous), ("successor", "当前", current)):
        value = report[side]
        lines += [f"## {title}", "", f"Calendar hash：{value['calendar_hash']}",
                  f"来源 commit：{snapshot['source_commit']}",
                  f"来源：{value['source']['url']}",
                  f"核读：{value['source']['reviewed_at']}；截止：{value['as_of']}",
                  f"窗口：{value['window']['start']} 至 {value['window']['end']}；"
                  f"原时区：{value['window']['timezone']}；展示时区：{value['local_timezone']}",
                  f"摘录 SHA256：{value['source']['sha256']}",
                  " / ".join(f"[{name}](../../{model.safe_path(source['read_path'])})"
                             for name, source in sorted(snapshot['files'].items())), ""]
    def appointment(event):
        if event is None:
            return "本端摘录/窗口未见"
        return (event['scheduled_at'] if event['time_precision'] == 'MINUTE'
                else event['scheduled_date'] + '（时刻 UNKNOWN）')
    lines += ["## 已保存的差异", "", "| 事件 / 报告期 | 前驱原预约 | 当前原预约 | 比较结果 | 来源行（前 / 后） |",
              "|---|---|---|---|---|"]
    for row in report['events']:
        before, after = row['predecessor_event'], row['successor_event']
        old_line = str(before['source_line']) if before else '未见'
        new_line = str(after['source_line']) if after else '未见'
        lines.append(f"| {row['event_id']} | {appointment(before)} | {appointment(after)} | "
                     f"{labels[row['change']]} | {old_line} / {new_line} |")
    lines += ["", f"Comparison hash：{report['comparison_hash']}",
              "Research / Human attention / Investment / Execution authority = NONE。", ""]
    return '\n'.join(lines).encode('utf-8')


def read_registered(collector, config) -> dict:
    """At most two explicit snapshots. A rejected predecessor preserves the current one."""
    current_config = ({key: value for key, value in config.items() if key != 'predecessor'}
                      if isinstance(config, dict) else config)
    current = _read_snapshot(collector, current_config)
    if current['status'] != STATUS:
        return current  # Never read a predecessor as fallback for a failed current input.
    info = {"status": "NOT_CONFIGURED", "meaning": "EXPLICIT_PAIR_NOT_OFFICIAL_REVISION_CHAIN",
            **model.AUTHORITY}
    if 'predecessor' not in config:
        return {**current, "comparison": info}
    files_before = collector.files
    stage = 'REGISTRATION'
    try:
        predecessor = config['predecessor']
        model.check(isinstance(predecessor, dict), 'comparison predecessor registration')
        model.check(predecessor.get('calendar_hash') != current['calendar_hash'], 'comparison self predecessor')
        stage = 'PREDECESSOR'
        previous = _read_snapshot(collector, predecessor, reserved_paths=COMPARISON_PATHS.values())
        if previous['status'] != STATUS:
            # _read_snapshot has restored this exact current-file inventory already.
            return {**current, "comparison": {**info, "status": "UNAVAILABLE_OR_REJECTED",
                    "failed_stage": stage, "error_type": previous.get('error_type'),
                    "diagnostic": previous.get('diagnostic'),
                    "limitation": "COMPARISON_GAP_NOT_NO_CHANGE_OR_CANCELLATION"}}
        stage = 'COMPARISON'
        with TemporaryDirectory(prefix='kernel-calendar-pair-') as tmp:
            folders = []
            for index, snapshot in enumerate((previous, current)):
                folder = Path(tmp) / str(index)
                folder.mkdir()
                for name in sorted(calendar.FILES):
                    (folder / name).write_bytes(collector.files[snapshot['files'][name]['read_path']])
                folders.append(folder)
            report = calendar.compare_calendars(*folders,
                predecessor_hash=previous['calendar_hash'], successor_hash=current['calendar_hash'])
        checked = collector.now()
        model.check(all(model.clock(snapshot['checked_at']) <= model.clock(checked)
                        for snapshot in (previous, current)), 'comparison check clock reversed')
        bodies = {"json": calendar._encoded(report),
                  "markdown": _comparison_markdown(report, previous, current)}
        stage = 'RETENTION'
        model.check(all(len(raw) <= calendar.MAX_SAVED_BYTES for raw in bodies.values()),
                    'comparison output byte budget')
        details = {name: collector.retain(COMPARISON_PATHS[name], raw) for name, raw in bodies.items()}
        return {**current, "comparison": {**info, "status": COMPARISON_STATUS,
                "checked_at": checked, "comparison_hash": report['comparison_hash'],
                "successor_hash": current['calendar_hash'], "predecessor": previous,
                "counts": report['counts'], "same_window": report['same_window'], "files": details}}
    except (ValueError, KeyError, TypeError, AttributeError, OSError, RuntimeError) as exc:
        collector.files = files_before
        labels = {'comparison self predecessor': 'SELF_PREDECESSOR',
                  'comparison predecessor registration': 'PREDECESSOR_REGISTRATION',
                  'COMPARISON_REVERSED_CLOCK': 'REVERSED_SOURCE_CLOCK',
                  'comparison check clock reversed': 'REVERSED_CHECK_CLOCK',
                  'comparison output byte budget': 'OUTPUT_BYTE_BUDGET',
                  'reading retention batch limit': 'RETENTION_BYTE_BUDGET',
                  'conflicting retained bytes': 'RETENTION_CONFLICT'}
        message = exc.args[0] if isinstance(exc, ValueError) and len(exc.args) == 1 else None
        code = labels.get(message, 'COMPARISON_REJECTED') if type(message) is str else 'COMPARISON_REJECTED'
        return {**current, "comparison": {**info, "status": "UNAVAILABLE_OR_REJECTED",
                "failed_stage": stage, "error_type": type(exc).__name__, "diagnostic": {"code": code},
                "limitation": "COMPARISON_GAP_NOT_NO_CHANGE_OR_CANCELLATION"}}


def navigation(saved: dict) -> bytes:
    """Same-R Markdown locators only; no live date or completion claim."""
    if saved.get("status") != STATUS:
        return b""
    path = model.safe_path(saved["files"]["calendar.md"]["read_path"])
    text = ("\n[研究日历：已保存的有限 BLS 预约](" + path + ")；原核读时刻保留，"
            "不是实时日历、实际发布确认或研究待办。\n")
    comparison = saved.get('comparison', {})
    if comparison.get('status') == COMPARISON_STATUS:
        details = comparison['files']
        text += ("\n[显式前驱比较](" + model.safe_path(details['markdown']['read_path']) + ") / "
                 "[比较 JSON](" + model.safe_path(details['json']['read_path']) + ")；"
                 "两端原件均在同一读取版本；缺行不等于取消。\n")
    elif comparison.get('status') == 'UNAVAILABLE_OR_REJECTED':
        text += "\n前驱比较读取失败；当前日历仍可读，不表示没有改期或发生取消。\n"
    else:
        text += "\n未登记显式前驱；未作版本比较，不表示没有改期。\n"
    return text.encode('utf-8')
