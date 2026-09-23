"""Explicit source-only preparation; no live queries, model, or write in CI."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import os
import socket
import subprocess
import textwrap

import pytest

from decision_kernel.runtime import industry_question_preparation as prep
from decision_kernel.runtime import declared_report_input as adopted
from decision_kernel.runtime import reviewed_full_input as full
from decision_kernel.runtime import industry_daily_question as industry
from decision_kernel.runtime import saved_research_once as once
from test_declared_report_input import setup_declared


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def deny(*args, **kwargs): raise AssertionError("preparation tests must be offline")
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)


def test_saved_plan_is_explicit_existing_question_not_model_authority():
    plan = json.loads(Path(prep.REQUEST).read_bytes())
    assert prep.check_plan(plan, lambda: "2026-09-23T01:00:00Z") == plan
    assert plan["permission"] == industry.PERMISSION
    assert plan["question"]["question_id"] == "jiangxi-copper-net-economic-exposure"
    assert plan["updates_start"] == "2026-03-27" and plan["updates_end"] == "2026-09-23"


@pytest.mark.parametrize("damage", ["permission", "scope", "expired", "future-window"])
def test_preparation_rejects_changed_plan(damage):
    plan = json.loads(Path(prep.REQUEST).read_bytes())
    if damage == "permission": plan["permission"] = {}
    elif damage == "scope": plan["origin_thscode"] = "RBZL.SHF"
    elif damage == "expired": plan["execute_before"] = "2026-09-23T00:00:00Z"
    else: plan["updates_end"] = "2026-09-24"
    with pytest.raises(ValueError): prep.check_plan(plan, lambda: "2026-09-23T01:00:00Z")


@pytest.mark.parametrize("title,expected", [
    ("江西铜业股份有限公司2026年半年度报告", "REQUIRES_BODY_REVIEW"),
    ("关于2025年年度报告的更正公告", "REQUIRES_BODY_REVIEW"),
    ("关于前期会计差错追溯调整", "REQUIRES_BODY_REVIEW"),
    ("2026年半年度报告摘要", "OUTSIDE_DECLARED_REPORT_CORRECTION_SCOPE"),
    ("董事会会议决议", "OUTSIDE_DECLARED_REPORT_CORRECTION_SCOPE"),
])
def test_correction_candidate_is_not_silently_a_no_update(title, expected):
    row = SimpleNamespace(title=title, announcement_id="unreviewed")
    assert prep.classify_update(row, {}) == expected
    assert prep.classify_update(row, {"unreviewed": object()}) == "BOUND_ORIGINAL_REPORT"


@pytest.mark.parametrize("image", [False, True])
def test_prepare_complete_documents_from_original_bytes_not_pdf_download(tmp_path, monkeypatch, image):
    c = setup_declared(tmp_path, monkeypatch, image=image)
    _, _, records = adopted.project(c.profile, c.declared_files)
    plan = {"titles": {"2026H1": c.context["issuer_documents"][0]["title"]}}
    docs, custody = prep.make_documents(c.profile, c.declared_files, records, plan, c.api, c.args["code"], c.args["clock"])
    assert docs[0]["pages"] == [{"page_number": p["page_number"], "text": p["text"]}
                               for p in c.context["issuer_documents"][0]["pages"]]
    assert custody == c.custody["documents"] and c.calls == [] and c.writes == []
    if image:
        assert full.referenced_reading(docs[0]["page_reading"])
        assert docs[0]["page_reading"]["reading_hash"] == c.context["issuer_documents"][0]["page_reading"]["reading_hash"]
    else: assert docs[0]["page_reading"] is None


@pytest.mark.parametrize("label,command", [
    ("industry-question-input-ready", "decision_kernel.runtime.industry_question_preparation"),
    ("declared-report-sources-ready", "decision_kernel.runtime.declared_report_sources")])
def test_actual_source_job_shell_selects_only_the_named_source_operation(tmp_path, label, command):
    text = Path('.github/workflows/stock-business-research.yml').read_text()
    job = text.split('  prepare-declared-report-sources:\n')[1].split('  deepseek-compatibility:\n')[0]
    assert 'research-api' not in job and 'secrets.' not in job and 'timeout-minutes: 12' in job
    assert 'industry-question-input-ready' in job and 'declared-report-sources-ready' in job
    step = job.split('      - name: Prepare only the exact declared public reports\n')[1].split('      - name:')[0]
    script = textwrap.dedent(step.split('        run: |\n')[1])
    marker = tmp_path / 'called'
    result = subprocess.run(['bash', '-c', 'python() { printf "%s\\n" "$@" > "$MARKER"; };\n' + script],
        env={"PATH": os.environ['PATH'], "MARKER": str(marker), "SOURCE_LABEL": label, "GITHUB_SHA": "a"*40},
        text=True, capture_output=True, timeout=10, check=False)
    assert result.returncode == 0, result.stderr
    assert marker.read_text().splitlines() == ['-m', command, '--code-commit', 'a'*40, '--output', 'declared-report-output']
    # Existing other jobs do not match the new label; concurrency/schedule untouched.
    others = text.replace('  prepare-declared-report-sources:\n' + job, '')
    assert 'industry-question-input-ready' not in others
    assert 'group: stock-business-first-v0' in others and 'schedule:' not in text
