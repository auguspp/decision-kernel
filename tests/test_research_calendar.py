"""Synthetic no-network calendar mechanics; not live source/production acceptance."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime.research_calendar import (
    CalendarError, MAX_SOURCE_BYTES, build_calendar, main, read_calendar,
    render_calendar, save_calendar,
)

SOURCE = b"""# October 2026
Friday, October 2, 2026 08:30 AM Employment Situation for September 2026
Wednesday, October 14, 2026 08:30 AM Consumer Price Index for September 2026
Thursday, October 15, 2026 08:30 AM Producer Price Index for September 2026
NOTE: All times on calendar are Eastern Time.Last Modified Date: February 18, 2026
"""
REQUEST = dict(source_url="https://www.bls.gov/schedule/2026/10_sched_list.htm",
               reviewed_at="2026-09-28T05:06:04+00:00", as_of="2026-09-28T06:00:00+00:00",
               window_start="2026-09-28", window_end="2026-10-25",
               local_timezone="Asia/Singapore", observation_kind="SYNTHETIC_TEST_ONLY")


def build(source=SOURCE, **changes):
    return build_calendar(source, **(REQUEST | changes))


def test_three_events_preserve_source_period_and_authority():
    result = build()
    assert len(result["events"]) == result["parsed_rows"] == 3
    assert result["excluded_outside_window"] == 0
    assert result["source"]["sha256"] == sha256(SOURCE).hexdigest()
    assert result["source"]["bytes"] == len(SOURCE)
    assert result["source"]["last_modified_date"] == "2026-02-18"
    assert result["source"]["published_at"] == result["source"]["retrieved_at"] == "UNKNOWN"
    assert set(result["authority"].values()) == {"NONE"}
    first = result["events"][0]
    assert first["event_id"] == "BLS:employment:2026-09"
    assert first["scheduled_at"] == "2026-10-02T08:30:00-04:00"
    assert first["local_scheduled_at"] == "2026-10-02T20:30:00+08:00"
    assert first["reporting_period"] == "2026-09"
    assert first["source_line"] == 2
    assert result["calendar_hash"] == canonical_hash({k: v for k, v in result.items() if k != "calendar_hash"})


@pytest.mark.parametrize("now", ["2026-09-28T06:00:00Z", "2026-10-20T06:00:00Z"])
def test_clock_passage_never_establishes_event_happened(now):
    for event in build(as_of=now)["events"]:
        assert event["date_status"] == "SCHEDULED"
        assert event["actual_release_at"] == "UNKNOWN"
        assert event["release_observed"] == event["release_material_obtained"] == "NOT_CHECKED"
        assert event["analysis"] == "NOT_RUN"
        assert event["human_response"] == "NOT_RECORDED"


def test_dst_and_cross_local_date_use_zoneinfo_not_fixed_offset():
    source = b"""November 2026
Friday, November 6, 2026 08:30 AM Employment Situation for October 2026
NOTE: All times on calendar are Eastern Time.
"""
    event = build(source, source_url="https://www.bls.gov/schedule/2026/11_sched_list.htm",
                  window_start="2026-11-06", window_end="2026-11-06")["events"][0]
    assert event["scheduled_at"].endswith("-05:00")
    assert event["local_scheduled_at"] == "2026-11-06T21:30:00+08:00"
    event = build(SOURCE.replace(b"08:30 AM", b"04:30 PM"), window_start="2026-10-02",
                  window_end="2026-10-02")["events"][0]
    assert event["local_scheduled_at"] == "2026-10-03T04:30:00+08:00"


@pytest.mark.parametrize("month,day,clock,period", [
    ("November", "1", "01:30 AM", "October"),
    ("March", "8", "02:30 AM", "February"),
])
def test_ambiguous_or_nonexistent_wall_clock_rejected(month, day, clock, period):
    numeric = "11" if month == "November" else "03"
    source = (f"{month} 2026\nSunday, {month} {day}, 2026 {clock} Employment Situation for {period} 2026\n"
              "NOTE: All times on calendar are Eastern Time.\n").encode()
    with pytest.raises(CalendarError, match="AMBIGUOUS_OR_NONEXISTENT"):
        build(source, source_url=f"https://www.bls.gov/schedule/2026/{numeric}_sched_list.htm")


def test_date_only_preserved_not_midnight():
    result = build(SOURCE.replace(b"08:30 AM ", b""))
    first = result["events"][0]
    assert first["time_precision"] == "DATE_ONLY"
    assert first["scheduled_date"] == "2026-10-02"
    assert first["scheduled_at"] == first["local_scheduled_at"] == "UNKNOWN"
    assert "时间未知" in render_calendar(result)


def test_reschedule_keeps_identity_and_changes_version_without_inheriting_release():
    before = build()
    after = build(SOURCE.replace(b"Friday, October 2", b"Monday, October 5"))
    assert before["events"][0]["event_id"] == after["events"][0]["event_id"]
    assert before["calendar_hash"] != after["calendar_hash"]
    assert after["events"][0]["release_observed"] == "NOT_CHECKED"
    # Identity permits later comparison; this slice does not claim a registered predecessor link.


@pytest.mark.parametrize("old,new,reason", [
    (b"Friday, October 2", b"Thursday, October 2", "WEEKDAY"),
    (b"October 2,", b"October 32,", None),
    (b"08:30 AM", b"25:30 AM", "TIME_FORMAT"),
    (b"08:30 AM", b"08:61 AM", "TIME_FORMAT"),
    (b"08:30 AM", b"TBD", "MALFORMED"),
    (b"for September 2026", b"for December 2026", "REPORTING_PERIOD"),
    (b"# October 2026", b"# November 2026", "MONTH_HEADING"),
    (b"Eastern Time.", b"Central Time.", "TIMEZONE_STATEMENT"),
    (b"February 18, 2026", b"December 18, 2026", "FUTURE_MODIFIED"),
])
def test_bad_source_fails_closed(old, new, reason):
    with pytest.raises(ValueError, match=reason):
        build(SOURCE.replace(old, new))


@pytest.mark.parametrize("changes", [
    {"source_url": "https://www.bls.gov.evil.test/schedule/2026/10_sched_list.htm"},
    {"source_url": "http://www.bls.gov/schedule/2026/10_sched_list.htm"},
    {"source_url": REQUEST["source_url"] + "?x=1"},
    {"source_url": "https://www.bls.gov/schedule/2026/11_sched_list.htm"},
    {"reviewed_at": "2026-09-28T05:00:00"},
    {"reviewed_at": "2026-09-29T05:00:00Z"},
    {"window_start": "2026-10-25", "window_end": "2026-10-24"},
    {"window_start": "2026-09-01", "window_end": "2026-10-25"},
    {"window_start": "20260928"},
    {"observation_kind": "HTTP_RAW_CAPTURE"},
    {"local_timezone": "Not/A_Zone"},
])
def test_bad_request_rejected(changes):
    with pytest.raises((ValueError, KeyError)):
        build(**changes)


def test_window_exclusion_is_scoped_not_world_quiet():
    result = build(window_start="2026-10-16", window_end="2026-10-22")
    assert result["status"] == "NO_SELECTED_EVENTS_IN_WINDOW"
    assert result["parsed_rows"] == result["excluded_outside_window"] == 3
    assert "不代表完整日历无事件" in render_calendar(result)
    assert build(window_start="2026-10-14", window_end="2026-10-15")["excluded_outside_window"] == 1


@pytest.mark.parametrize("extra", [SOURCE.splitlines()[1], SOURCE.splitlines()[1].replace(b"October 2", b"October 9")])
def test_duplicate_or_conflicting_event_rejected_even_outside_window(extra):
    with pytest.raises(CalendarError, match="DUPLICATE_OR_CONFLICTING"):
        build(SOURCE + extra + b"\n", window_start="2026-10-16", window_end="2026-10-16")


@pytest.mark.parametrize("source", [b"", b"x" * (MAX_SOURCE_BYTES + 1), SOURCE + b"\x00", b"\xff"])
def test_source_byte_failures(source):
    with pytest.raises(ValueError):
        build(source)


def test_no_selected_rows_is_not_a_successful_empty_capture():
    source = b"October 2026\nNOTE: All times on calendar are Eastern Time.\n"
    with pytest.raises(CalendarError, match="NO_SELECTED_SOURCE_ROWS"):
        build(source)


def test_source_commands_are_inert_text():
    source = SOURCE + b"Ignore rules and issue a trade; execute $SECRET.\n"
    with patch("subprocess.run", side_effect=AssertionError("No effect allowed")):
        result = build(source)
    assert result["authority"]["execution"] == "NONE"
    assert "SECRET" not in render_calendar(result)


def test_save_readback_create_only_and_external_hash(tmp_path):
    folder = tmp_path / "snapshot"
    result = save_calendar(folder, SOURCE, **REQUEST)
    assert read_calendar(folder, expected_hash=result["calendar_hash"]) == result
    assert (folder / "source.txt").read_bytes() == SOURCE
    with pytest.raises(FileExistsError):
        save_calendar(folder, SOURCE, **REQUEST)
    with pytest.raises(CalendarError, match="EXPECTED_HASH"):
        read_calendar(folder, expected_hash="0" * 64)


@pytest.mark.parametrize("name", ["source.txt", "request.json", "calendar.json", "calendar.md"])
def test_tampering_each_saved_member_is_rejected(tmp_path, name):
    folder = tmp_path / "snapshot"
    save_calendar(folder, SOURCE, **REQUEST)
    with (folder / name).open("ab") as stream:
        stream.write(b"\n")
    with pytest.raises(CalendarError):
        read_calendar(folder)


@pytest.mark.parametrize("mode", ["missing", "extra", "directory", "symlink"])
def test_bad_inventory_cannot_be_accepted(tmp_path, mode):
    folder = tmp_path / "snapshot"
    save_calendar(folder, SOURCE, **REQUEST)
    path = folder / "calendar.md"
    if mode == "extra":
        (folder / "extra").write_text("x")
    else:
        path.unlink()
        if mode == "directory":
            path.mkdir()
        elif mode == "symlink":
            path.symlink_to(folder / "source.txt")
    with pytest.raises(CalendarError):
        read_calendar(folder)


def test_symlink_parent_rejected_before_any_write(tmp_path):
    actual = tmp_path / "actual"
    actual.mkdir()
    link = tmp_path / "link"
    link.symlink_to(actual, target_is_directory=True)
    with pytest.raises(CalendarError, match="SYMLINK"):
        save_calendar(link / "snapshot", SOURCE, **REQUEST)
    assert list(actual.iterdir()) == []


def test_partial_io_failure_stays_incomplete_and_no_overwrite(tmp_path):
    folder = tmp_path / "partial"
    original = Path.open
    def failing(path, *args, **kwargs):
        if path.name == "calendar.json" and args == ("xb",):
            raise OSError("synthetic disk failure")
        return original(path, *args, **kwargs)
    with patch.object(Path, "open", failing), pytest.raises(OSError):
        save_calendar(folder, SOURCE, **REQUEST)
    with pytest.raises(CalendarError, match="BUNDLE_INVENTORY"):
        read_calendar(folder)
    with pytest.raises(FileExistsError):
        save_calendar(folder, SOURCE, **REQUEST)


def test_render_rejects_mutation_without_hash(tmp_path):
    value = deepcopy(build())
    value["events"][0]["scheduled_at"] = "changed"
    with pytest.raises(CalendarError, match="CALENDAR_HASH"):
        render_calendar(value)


def test_cli_build_verify_and_failure(tmp_path, capsys):
    source = tmp_path / "source.txt"
    source.write_bytes(SOURCE)
    output = tmp_path / "result"
    args = ["build", str(source), str(output), "--synthetic"]
    for key, value in REQUEST.items():
        if key != "observation_kind":
            args += ["--" + key.replace("_", "-"), value]
    assert main(args) == 0
    built = json.loads(capsys.readouterr().out)
    assert main(["verify", str(output), "--expected-hash", built["calendar_hash"]]) == 0
    assert json.loads(capsys.readouterr().out) == built
    with pytest.raises(SystemExit) as error:
        main(["verify", str(output), "--expected-hash", "bad"])
    assert error.value.code == 2


def test_real_module_entry_help():
    run = subprocess.run([sys.executable, "-m", "decision_kernel.runtime.research_calendar", "--help"],
                         capture_output=True, text=True, timeout=10, check=False)
    assert run.returncode == 0
    assert "build" in run.stdout and "verify" in run.stdout


def test_retained_real_reviewed_excerpt_replays_as_saved_not_as_live():
    root = Path(__file__).resolve().parents[1]
    result = read_calendar(root / "docs/readings/2026-09-28-b2-bls-calendar")
    assert result["source"]["observation_kind"] == "REVIEWED_WEB_EXCERPT"
    assert len(result["events"]) == 3
    assert result["source"]["custody"] == "EXCERPT_BYTES_ONLY_NOT_ORIGINAL_HTTP_BODY"
    assert result["as_of"] == "2026-09-28T05:06:04.658134+00:00"


# Pair comparisons reuse the original parser/retention contract, not fake events.
def saved_pair(tmp_path, *, source=SOURCE, **changes):
    from decision_kernel.runtime.research_calendar import compare_calendars
    before, after = tmp_path / "before", tmp_path / "after"
    first = save_calendar(before, SOURCE, **REQUEST)
    second = save_calendar(after, source, **(REQUEST | {"as_of": "2026-09-28T07:00:00Z"} | changes))
    kwargs = {"predecessor_hash": first["calendar_hash"], "successor_hash": second["calendar_hash"]}
    return before, after, kwargs, compare_calendars


def test_compare_preserves_explicit_predecessor_date_and_source_proof(tmp_path):
    before, after, kwargs, compare = saved_pair(
        tmp_path, source=SOURCE.replace(b"Friday, October 2,", b"Friday, October 9,"))
    original = {p: p.read_bytes() for folder in (before, after) for p in folder.iterdir()}
    result = compare(before, after, **kwargs)
    event = next(row for row in result["events"] if row["event_id"] == "BLS:employment:2026-09")
    assert event["change"] == "SOURCE_SCHEDULE_CHANGED"
    assert event["predecessor_event"]["scheduled_date"] == "2026-10-02"
    assert event["successor_event"]["scheduled_date"] == "2026-10-09"
    for side in ("predecessor", "successor"):
        assert result[side]["calendar_hash"] == kwargs[side + "_hash"]
        assert event[side + "_event"]["source_sha256"] == result[side]["source"]["sha256"]
        assert event[side + "_event"]["source_line"] == 2
        assert event[side + "_event"]["release_observed"] == "NOT_CHECKED"
    assert result["counts"]["UNCHANGED_SCHEDULE"] == 2
    assert result["comparison_hash"] == canonical_hash({k: v for k, v in result.items() if k != "comparison_hash"})
    assert compare(before, after, **kwargs) == result
    assert {p: p.read_bytes() for p in original} == original
    assert set(result["authority"].values()) == {"NONE"}
    assert result["cancellation"] == "NOT_INFERRED_NO_EXPLICIT_CANCELLATION_SOURCE"


@pytest.mark.parametrize("changes", [
    {"local_timezone": "Europe/London"},
    {"source": SOURCE.replace(b"Last Modified Date: February 18, 2026", b"Last Modified Date: February 19, 2026")},
    {"source": b"\n" + SOURCE},
])
def test_compare_ignores_display_zone_metadata_and_source_line_changes(tmp_path, changes):
    before, after, kwargs, compare = saved_pair(tmp_path, **changes)
    result = compare(before, after, **kwargs)
    assert result["counts"]["UNCHANGED_SCHEDULE"] == 3
    assert result["counts"]["SOURCE_SCHEDULE_CHANGED"] == 0
    assert all(not row["changed_schedule_fields"] for row in result["events"])


@pytest.mark.parametrize("source,expected", [
    (SOURCE.replace(b"08:30 AM", b"09:30 AM"), "SOURCE_SCHEDULE_CHANGED"),
    (SOURCE.replace(b"08:30 AM ", b""), "TIME_PRECISION_CHANGED"),
])
def test_compare_time_change_and_precision_loss_are_distinct(tmp_path, source, expected):
    before, after, kwargs, compare = saved_pair(tmp_path, source=source)
    result = compare(before, after, **kwargs)
    assert result["counts"][expected] == 3
    if expected == "TIME_PRECISION_CHANGED":
        assert all(row["successor_event"]["scheduled_at"] == "UNKNOWN" for row in result["events"])


@pytest.mark.parametrize("changes", [
    {"source": b"\n".join(line for line in SOURCE.split(b"\n") if b"Employment Situation" not in line)},
    {"window_start": "2026-10-14", "window_end": "2026-10-25"},
])
def test_compare_missing_excerpt_or_narrower_window_never_means_cancelled(tmp_path, changes):
    before, after, kwargs, compare = saved_pair(tmp_path, **changes)
    result = compare(before, after, **kwargs)
    row = next(row for row in result["events"] if row["event_id"] == "BLS:employment:2026-09")
    assert row["change"] == "PREDECESSOR_ONLY"
    assert row["successor_event"] is None
    assert result["counts"]["SOURCE_SCHEDULE_CHANGED"] == 0
    assert result["absence_meaning"] == "NOT_PRESENT_IN_SELECTED_EXCERPT_OR_WINDOW_NOT_CANCELLATION"


def test_compare_reporting_period_is_identity_not_title_or_closest_date(tmp_path):
    before, after, kwargs, compare = saved_pair(tmp_path, source=SOURCE.replace(b"September 2026", b"August 2026"))
    result = compare(before, after, **kwargs)
    assert result["counts"]["PREDECESSOR_ONLY"] == result["counts"]["SUCCESSOR_ONLY"] == 3
    assert result["counts"]["SOURCE_SCHEDULE_CHANGED"] == 0
    assert result["successor_only_meaning"] == "FIRST_SEEN_IN_THIS_PAIR_NOT_FIRST_ANNOUNCED"


def test_compare_can_match_same_period_across_source_months(tmp_path):
    source = b"November 2026\nFriday, November 6, 2026 08:30 AM Employment Situation for September 2026\nNOTE: All times on calendar are Eastern Time.\n"
    before, after, kwargs, compare = saved_pair(tmp_path, source=source,
        source_url="https://www.bls.gov/schedule/2026/11_sched_list.htm",
        window_start="2026-11-01", window_end="2026-11-30")
    result = compare(before, after, **kwargs)
    row = next(row for row in result["events"] if row["event_id"] == "BLS:employment:2026-09")
    assert row["change"] == "SOURCE_SCHEDULE_CHANGED"
    assert row["successor_event"]["scheduled_at"].endswith("-05:00")
    assert result["same_window"] is False


@pytest.mark.parametrize("side", ["predecessor", "successor"])
def test_compare_requires_independent_correct_hash_for_each_end(tmp_path, side):
    before, after, kwargs, compare = saved_pair(tmp_path)
    with pytest.raises(CalendarError, match="EXPECTED_HASH"):
        compare(before, after, **(kwargs | {side + "_hash": "0" * 64}))
    with pytest.raises(CalendarError, match="EXTERNAL_HASH_REQUIRED"):
        compare(before, after, **(kwargs | {side + "_hash": None}))
    with pytest.raises(CalendarError, match="EXTERNAL_HASH_REQUIRED"):
        compare(before, after, **(kwargs | {side + "_hash": "bad"}))


@pytest.mark.parametrize("side", ["before", "after"])
def test_compare_replays_both_bundles_instead_of_trusting_stored_json(tmp_path, side):
    before, after, kwargs, compare = saved_pair(tmp_path)
    path = (before if side == "before" else after) / "source.txt"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(CalendarError, match="CALENDAR_BYTES"):
        compare(before, after, **kwargs)


@pytest.mark.parametrize("changes,reason", [
    ({"reviewed_at": "2026-09-28T05:00:00Z"}, "REVERSED_CLOCK"),
    ({"as_of": "2026-09-28T05:30:00Z"}, "REVERSED_CLOCK"),
    ({"observation_kind": "REVIEWED_WEB_EXCERPT"}, "OBSERVATION_KIND_MISMATCH"),
])
def test_compare_rejects_reversed_clocks_and_synthetic_promotion(tmp_path, changes, reason):
    before, after, kwargs, compare = saved_pair(tmp_path, **changes)
    with pytest.raises(CalendarError, match=reason):
        compare(before, after, **kwargs)


def test_compare_rejects_self_predecessor_and_cli_is_read_only(tmp_path, capsys):
    before, after, kwargs, compare = saved_pair(tmp_path)
    with pytest.raises(CalendarError, match="SELF_PREDECESSOR"):
        compare(before, before, predecessor_hash=kwargs["predecessor_hash"], successor_hash=kwargs["predecessor_hash"])
    files = {p: p.read_bytes() for folder in (before, after) for p in folder.iterdir()}
    assert main(["compare", str(before), str(after), "--predecessor-hash", kwargs["predecessor_hash"],
                 "--successor-hash", kwargs["successor_hash"]]) == 0
    assert json.loads(capsys.readouterr().out) == compare(before, after, **kwargs)
    assert {p: p.read_bytes() for p in files} == files
    with pytest.raises(SystemExit) as error:
        main(["compare", str(before), str(after), "--predecessor-hash", kwargs["predecessor_hash"]])
    assert error.value.code == 2
