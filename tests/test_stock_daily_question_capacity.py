"""Finite reservation and publication capacity, without invoking any executor."""
from copy import deepcopy
from datetime import date, timedelta

import pytest

from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import stock_daily_question as daily
from decision_kernel.runtime import stock_question_host as host
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import reviewed_question_reading as reader
from test_stock_daily_question import setup_daily


def view(case):
    return daily.work_tree(case.api)


def scope(case, day="2026-09-18", execution_id=None):
    return {"market_session": day, "execution_id": execution_id or host.question_execution(
        case.q["security_id"], case.q["question_id"])[0]}


def marker(case, slot, day, *, day_copy=True, execution_id=None):
    code = case.args["code"]
    case.api.heads[intake.WORK_REF] = code
    value = {**scope(case, day, execution_id), "policy": deepcopy(daily.POLICY)}
    raw = once.raw(value)
    case.api.files[code][daily.PREFIX + f"slots/{slot:02}/prepare.json"] = raw
    if day_copy:
        case.api.files[code][daily.PREFIX + f"days/{day}/prepare.json"] = raw


def test_tenth_slot_is_last_even_when_day_saves_are_incomplete(tmp_path, monkeypatch):
    case = setup_daily(tmp_path, monkeypatch)
    for slot in range(1, 10):
        marker(case, slot, (date(2026, 9, 18) + timedelta(days=slot - 1)).isoformat(),
               execution_id="stock-question-" + f"{slot:064x}", day_copy=False)
    commit, rows = view(case)
    following = scope(case, "2026-10-01")
    paths = daily.reservation_plan(case.api, commit, rows, following)
    assert paths == (daily.PREFIX + "slots/10/", daily.PREFIX + "days/2026-10-01/")
    marker(case, 10, "2026-09-30", execution_id="stock-question-" + "e" * 64)
    commit, rows = view(case)
    with pytest.raises(once.TrialError, match="DAILY_MARKET_DAY_LIMIT_REACHED"):
        daily.reservation_plan(case.api, commit, rows, following)


@pytest.mark.parametrize("same_day", [True, False])
def test_slot_without_day_or_question_still_consumes_both_identities(tmp_path, monkeypatch, same_day):
    case = setup_daily(tmp_path, monkeypatch)
    marker(case, 1, "2026-09-18", day_copy=False)
    commit, rows = view(case)
    following = scope(case, "2026-09-18" if same_day else "2026-09-19")
    with pytest.raises(once.TrialError, match="DAILY_MARKET_DAY_ALREADY_CONSUMED" if same_day else "DAILY_QUESTION_ALREADY_RESERVED"):
        daily.reservation_plan(case.api, commit, rows, following)


def test_competing_dates_choose_same_create_only_slot(tmp_path, monkeypatch):
    case = setup_daily(tmp_path, monkeypatch)
    commit, rows = view(case)
    first = daily.reservation_plan(case.api, commit, rows, scope(case))
    second = daily.reservation_plan(case.api, commit, rows, scope(case, "2026-09-19"))
    assert first[0] == second[0] == daily.PREFIX + "slots/01/"
    case.api.heads[intake.WORK_REF] = case.args["code"]
    owners = []
    for n in range(2):
        out = tmp_path / str(n); out.mkdir()
        owners.append(once.Retainer(case.api, {"prefix": first[0], "id": "synthetic",
                                              "work_ref": intake.WORK_REF}, case.args["code"], out))
    owners[0].save("prepare.json", {"scope": "first"})
    with pytest.raises(ValueError):
        owners[1].save("prepare.json", {"scope": "second"})
    assert owners[1].uncertain
    assert not case.calls


def capacity_input(case):
    _, packet, _, _, _ = host._question_inputs(api=case.api, code=case.args["code"],
        request=daily.base_request(case.request), clock=case.args["clock"])
    rs = case.q["reading_source"]
    state = once.identity._json(case.api.file(rs["path"], rs["ref"]))
    return packet, state


def retain_case_files(case, prefix, names):
    case.api.heads[intake.WORK_REF] = case.args["code"]
    for name in names:
        # Distinct retained bytes are conservatively distinct publication blobs.
        body = {"path": prefix + name, "question_source": case.request["question_source"]}
        case.api.files[case.args["code"]][prefix + name] = once.raw(body)


def test_shared_file_capacity_includes_legacy_and_complete_new_result(tmp_path, monkeypatch):
    case = setup_daily(tmp_path, monkeypatch)
    for key in ("1", "2"):
        retain_case_files(case, reader.PREFIX + key * 64 + "/", reader.CORE)
    retain_case_files(case, reader.PREFIX + "3" * 64 + "/", ("prepare.json",))
    legacy = intake.execution(case.q["case_id"])[1]
    retain_case_files(case, legacy, ("prepare.json", "candidate.json", "input.json"))
    packet, state = capacity_input(case)
    commit, rows = view(case)
    #19 old CORE +1 shared declaration +3 legacy +9 new CORE =32 files.
    daily.capacity(case.api, commit, rows, state, packet)
    retain_case_files(case, legacy, ("failure.json",))
    commit, rows = view(case)
    with pytest.raises(once.TrialError, match="DAILY_READING_CAPACITY_UNAVAILABLE"):
        daily.capacity(case.api, commit, rows, state, packet)


def test_current_partial_root_reserves_its_remaining_core_files(tmp_path, monkeypatch):
    case = setup_daily(tmp_path, monkeypatch)
    for key in ("1", "2", "3"):
        retain_case_files(case, reader.PREFIX + key * 64 + "/", reader.CORE)
    retain_case_files(case, case.prefix, ("prepare.json",))
    packet, state = capacity_input(case)
    commit, rows = view(case)
    with pytest.raises(once.TrialError, match="DAILY_READING_CAPACITY_UNAVAILABLE"):
        daily.capacity(case.api, commit, rows, state, packet)


def test_partial_executions_count_toward_original_eight_execution_bound(tmp_path, monkeypatch):
    case = setup_daily(tmp_path, monkeypatch)
    for key in range(1, 9):
        retain_case_files(case, reader.PREFIX + f"{key:064x}/", ("prepare.json",))
    packet, state = capacity_input(case)
    commit, rows = view(case)
    with pytest.raises(once.TrialError, match="DAILY_READING_CAPACITY_UNAVAILABLE"):
        daily.capacity(case.api, commit, rows, state, packet)
