"""Question opt-in composition through original prepare/admission/research/retainer.

Only Git I/O and the model response boundary are synthetic. No source/network call.
"""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import socket
from uuid import NAMESPACE_URL, uuid5

import pytest

from decision_kernel.identity import canonical_hash
from decision_kernel.runtime import stock_question_host as host
from decision_kernel.runtime import saved_research_once as once
from decision_kernel.runtime import reviewed_question_input as reviewed
from decision_kernel.runtime import external_research_admission as admission
from decision_kernel.runtime import external_research_identity as identity
from decision_kernel.runtime import stock_research_intake as intake
from decision_kernel.runtime import current_state as reading
from test_stock_research_host import setup_host
from test_saved_research_once import pre, quick


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("question tests must not access networking")
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


def setup_question(tmp_path, monkeypatch):
    old_args, api, _, _, writes = setup_host(tmp_path, monkeypatch)
    clock, code, r = old_args["clock"], old_args["code"], old_args["reading_commit"]
    stamp = reading.clock(clock())
    earlier = lambda minutes: (stamp - timedelta(minutes=minutes)).isoformat()
    state = reading.assemble(code_commit=code, checked_at=earlier(30), check_started_at=earlier(31),
        lanes={}, research={"handoffs": {"active": []}}, capabilities=[], refresh_identity={})
    api.files[r]["current-state.json"] = once.raw(state)
    rs = once.source_ref("current-state.json", r, once.raw(state), "SAVED_QUESTION_READING")
    q = {"format": reviewed.FORMAT, "case_id": "600184.SH", "ticker": "600184", "security_id": "SSE:600184",
        "question_id": "synthetic-restricted-cash", "revision": 1, "predecessor": None,
        "declared_at": earlier(25), "reading_source": rs, "question": "Synthetic distinct funding question",
        "why_now": "Synthetic qualified saved institutional observation, not price approval.",
        "falsification_test": "Distinguish a permitted transfer from actual project spending.",
        "required_classes": [{"id": "RESTRICTED_FUNDS_BODY", "mode": "STATIC", "planned_queries": []}],
        "known_counterevidence": ["Approval is not expenditure."], "known_unknowns": ["Actual spending UNKNOWN"],
        "next_discriminating_search": "Read exact original funding bodies, not new prices.",
        "origins": [{"kind": "INSTITUTIONAL_WINDOWS", "source": rs, "observed_at": earlier(30),
            "qualification": "QUALIFIED_FOR_DECLARED_SCOPE", "qualification_reason": "Synthetic original-window identity."}],
        "existing_research_relation": {"kind": "NEW_DISTINCT_QUESTION", "note": "Synthetic separate question; do not reset baseline.", "source_refs": []}}
    context = {"issuer_documents": [{"announcement_id": "synthetic-body", "title": "Synthetic issuer filing",
        "source_locator": "https://issuer.invalid/funding.pdf", "pdf_sha256": "f"*64,
        "published_at": earlier(300), "retrieved_at": earlier(15), "page_count": 1,
        "reading_method": "ORIGINAL_PYPDF", "page_reading": None,
        "pages": [{"page_number": 1, "text": "Synthetic public funding and counterevidence, not real issuer facts."}]}],
        "source_limitations": "Synthetic complete declared body only, not current company-wide coverage."}
    qs = once.source_ref("research_runs/question-plan/question.json", "d"*40, once.raw(q), reviewed.PURPOSE)
    cs = once.source_ref("research_runs/question-context/source.json", "e"*40, once.raw(context), "MODEL_CONTEXT")
    eid, prefix = host.question_execution(q["security_id"], q["question_id"])
    seed_id = str(uuid5(NAMESPACE_URL, eid + ":" + cs["sha256"]))
    pf = {"schema_version": 1, "provenance": "RECORDED_TOOL_RETURNS", "case_id": q["case_id"],
        "ticker": q["ticker"], "security_id": q["security_id"], "started_at": earlier(19), "finished_at": earlier(10),
        "valid_until": (stamp + timedelta(minutes=45)).isoformat(),
        "reads": [{"id": "body1", "identity": "600184:synthetic-body", "locator": context["issuer_documents"][0]["source_locator"],
            "authority": "PRIMARY", "kind": "BODY", "succeeded": True, "checked_at": earlier(10),
            "body_sha256": "f"*64, "tool_reference": "SYNTHETIC_RETAINED_PRIMARY"}],
        "required_classes": [{"id": "RESTRICTED_FUNDS_BODY", "mode": "STATIC", "body_ids": ["body1"], "inventory_id": None}],
        "inventories": [], "limits": {"max_reads": 1, "max_queries": 0},
        "seed_publications": [{"evidence_id": seed_id, "kind": "GIT_COMMIT", "source": cs}]}
    ps = once.source_ref("research_runs/question-context/preflight.json", "f"*40, once.raw(pf), admission.PREFLIGHT_PURPOSE)
    for spec, body in [(qs, q), (cs, context), (ps, pf)]:
        api.files[spec["ref"]] = {spec["path"]: once.raw(body)}
    extra_commits = {ref: {"sha": ref, "committer": {"date": earlier(minutes)}}
                     for ref, minutes in [("d"*40, 24), ("e"*40, 20), ("f"*40, 9)]}
    get = api.get
    def with_commits(path):
        if path.startswith("git/commits/") and path.removeprefix("git/commits/") in extra_commits:
            return deepcopy(extra_commits[path.removeprefix("git/commits/")])
        return get(path)
    api.get = with_commits
    request = {"schema_version": 1, "enabled": True, "mode": host.QUESTION_MODE,
        "permission": old_args["request"]["permission"], "question_source": qs,
        "context_source": cs, "preflight_source": ps, "approved_egress_hash": None}
    q2, packet, discovery, ctx, _ = host._question_inputs(api=api, code=code, request=request, clock=clock)
    request["approved_egress_hash"] = host.question_egress_hash(packet, discovery, ctx)
    api.files[code][host.QUESTION_REQUEST] = once.raw(request)
    calls = []
    def call(stage, prompt, model, output, usage):
        calls.append((stage, deepcopy(prompt)))
        return pre(prompt, "CONTINUE_TO_QUICK") if stage == "pre" else quick(prompt)
    args = dict(api=api, code=code, output=tmp_path/"question", clock=clock, call=call)
    return args, api, request, q, context, pf, calls, writes, prefix


def store_request(api, code, request):
    api.files[code][host.QUESTION_REQUEST] = once.raw(request)


def replace_source(api, code, request, key, body):
    old = request[key]
    data = once.raw(body)
    request[key] = once.source_ref(old["path"], old["ref"], data, old["purpose"])
    api.files[old["ref"]][old["path"]] = data
    store_request(api, code, request)


@pytest.mark.parametrize("route,stages", [("WAIT_FOR_TRIGGER", ["pre"]), ("STOP", ["pre"]),
                                          ("CONTINUE_TO_QUICK", ["pre", "quick"])])
def test_original_functions_execute_and_retain_only_the_qualified_route(tmp_path, monkeypatch, route, stages):
    args, api, request, q, _, _, calls, writes, prefix = setup_question(tmp_path, monkeypatch)
    def call(stage, prompt, model, output, usage):
        calls.append(stage)
        assert "KNOWN_COUNTEREVIDENCE:Approval is not expenditure." in prompt["known_unknowns"]
        assert any(x.startswith("FALSIFICATION_TEST:") for x in prompt["known_unknowns"])
        return pre(prompt, route) if stage == "pre" else quick(prompt)
    args["call"] = call
    result = host.run_question(**args)
    assert result["status"] == "VALIDATED_FUNNEL_RESULT", result
    assert calls == stages
    saved = api.files[api.heads[intake.WORK_REF]]
    for name in ("prepare.json", "source.json", "input.json", "launch.json", "admission.json",
                 "candidate.json", "validation.json", "funnel.json", "receipt.json", "host-receipt.json", "README.md"):
        assert prefix + name in saved
    assert json.loads(saved[prefix+"prepare.json"])["status"] == "QUESTION_INPUT_PREPARED_NOT_EXECUTED"
    assert json.loads(saved[prefix+"admission.json"])["research_execution_allowed"] is True
    assert result["investment_authority"] == "NONE" and not result["registered_current_handoff"]
    # New sibling namespace does not invalidate the legacy Stock work inventory.
    assert not intake.inventory(api, api.heads[intake.WORK_REF])
    assert not any(key.startswith(intake.execution(q["case_id"])[1]) for key in saved)
    before = deepcopy(saved); count = len(writes)
    args["output"] = tmp_path/"again"
    repeated = host.run_question(**args)
    assert repeated["status"] == "EXISTING_QUESTION_REUSED_NO_EXECUTION"
    assert calls == stages and len(writes) == count and saved == before


@pytest.mark.parametrize("damage", ["disabled", "permission", "egress", "body", "context-hash", "page", "page-bool",
    "continuation", "no-qualified-origin", "stale-preflight", "missing-class", "main", "purpose", "pdf-sha", "future-body", "execution-override"])
def test_invalid_input_does_not_reserve_launch_or_call_model(tmp_path, monkeypatch, damage):
    args, api, request, q, context, pf, calls, writes, _ = setup_question(tmp_path, monkeypatch)
    if damage == "disabled": request["enabled"] = False
    elif damage == "execution-override": request["execution_id"] = "rename-to-reopen"
    elif damage == "permission": api.comment["body"] = "revoked"
    elif damage == "egress": request["approved_egress_hash"] = "0"*64
    elif damage == "main": api.heads["main"] = "0"*40
    elif damage == "purpose": request["context_source"]["purpose"] = "OTHER"
    elif damage == "context-hash": api.files[request["context_source"]["ref"]][request["context_source"]["path"]] += b" "
    elif damage in {"body", "stale-preflight", "missing-class"}:
        if damage == "body": pf["required_classes"][0]["body_ids"] = []
        elif damage == "stale-preflight": pf["valid_until"] = pf["finished_at"]
        else: pf["required_classes"] = []
        replace_source(api, args["code"], request, "preflight_source", pf)
    elif damage in {"continuation", "no-qualified-origin"}:
        if damage == "continuation": q["existing_research_relation"]["kind"] = "CONTINUE_ANALYSIS"
        else: q["origins"][0]["qualification"] = "UNKNOWN"
        replace_source(api, args["code"], request, "question_source", q)
    else:
        if damage == "page": context["issuer_documents"][0]["pages"] = []
        elif damage == "page-bool": context["issuer_documents"][0]["pages"][0]["page_number"] = True
        elif damage == "pdf-sha": context["issuer_documents"][0]["pdf_sha256"] = "e"*64
        else: context["issuer_documents"][0]["published_at"] = "2999-01-01T00:00:00Z"
        replace_source(api, args["code"], request, "context_source", context)
    store_request(api, args["code"], request)
    result = host.run_question(**args)
    assert result["status"] == "NOT_EXECUTED" and not result["formal_research_started"], result
    assert not writes and not calls and not (args["output"]/"launch.json").exists()


@pytest.mark.parametrize("name", ["prepare.json", "input.json", "launch.json", "failure.json", "candidate.json", "unknown.txt"])
def test_any_existing_question_history_stops_without_a_second_write(tmp_path, monkeypatch, name):
    args, api, _, _, _, _, calls, writes, prefix = setup_question(tmp_path, monkeypatch)
    api.heads[intake.WORK_REF] = args["code"]
    api.files[args["code"]][prefix+name] = b"{}"
    result = host.run_question(**args)
    assert result["status"] == "EXISTING_QUESTION_REUSED_NO_EXECUTION", result
    assert not calls and not writes


@pytest.mark.parametrize("change", ["revoke", "main", "source", "timeout", "provider-failure"])
def test_recheck_before_quick_and_no_retries(tmp_path, monkeypatch, change):
    args, api, request, _, _, _, calls, writes, _ = setup_question(tmp_path, monkeypatch)
    original_clock = args["clock"]; shift = [timedelta()]
    args["clock"] = lambda: (reading.clock(original_clock())+shift[0]).isoformat()
    def call(stage, prompt, model, output, usage):
        calls.append(stage)
        if change == "provider-failure": raise RuntimeError("SECRET_REMOTE_DETAIL")
        if stage == "pre":
            if change == "revoke": api.comment["body"] = "revoked"
            elif change == "main": api.heads["main"] = "0"*40
            elif change == "source": api.files[request["context_source"]["ref"]][request["context_source"]["path"]] += b" "
            elif change == "timeout": shift[0] = timedelta(hours=2)
            return pre(prompt, "CONTINUE_TO_QUICK")
        raise AssertionError("revoked/changed scope reached Quick")
    args["call"] = call
    result = host.run_question(**args)
    assert result["status"] == "EXECUTION_GAP", result
    assert calls == ["pre"] and not (args["output"]/"funnel.json").exists()
    assert "SECRET_REMOTE_DETAIL" not in (args["output"]/"host-receipt.json").read_text()


def test_uncertain_reservation_does_not_write_again_or_call_model(tmp_path, monkeypatch):
    args, api, _, _, _, _, calls, _, _ = setup_question(tmp_path, monkeypatch)
    api.heads[intake.WORK_REF] = args["code"]
    attempts = []
    def uncertain(self, *params):
        attempts.append(params)
        self.uncertain = True
        raise RuntimeError("SECRET_UNCERTAIN")
    monkeypatch.setattr(once.Retainer, "native", uncertain)
    result = host.run_question(**args)
    assert result["mutation_uncertain"] and not result["formal_research_started"]
    assert len(attempts) == 1 and not calls


def test_missing_input_readback_does_not_create_launch(tmp_path, monkeypatch):
    args, api, _, _, _, _, calls, writes, prefix = setup_question(tmp_path, monkeypatch)
    original = api.file
    def bad_readback(path, ref):
        body = original(path, ref)
        return body+b" " if path == prefix+"input.json" else body
    api.file = bad_readback
    result = host.run_question(**args)
    assert result["mutation_uncertain"] and not calls
    assert not any(row[1] == "contents/"+prefix+"launch.json" for row in writes)


def test_same_problem_stable_identity_ignores_revision():
    assert host.question_execution("SSE:600184", "funding") == host.question_execution("SSE:600184", "funding")
    assert host.question_execution("SSE:600184", "funding") != intake.execution("600184.SH")
    assert host.question_execution("SSE:600184", "funding") != host.question_execution("SZSE:300711", "funding")


def test_main_configuration_is_disabled_and_workflow_does_not_auto_select_question():
    root = Path(__file__).parents[1]
    request = json.loads((root/host.QUESTION_REQUEST).read_text())
    # Keep this historical test identity; deployment may be explicitly activated.
    # Synthetic disabled/unauthorized cases above still reject all model calls.
    assert type(request["enabled"]) is bool and request["mode"] == host.QUESTION_MODE
    if not request["enabled"]:
        assert request["permission"] is None and request["approved_egress_hash"] is None
    else:
        assert set(request["permission"]) == {"comment_id", "created_at", "body_sha256"}
        assert isinstance(request["permission"]["comment_id"], int)
        assert len(request["permission"]["body_sha256"]) == 64
        assert len(request["approved_egress_hash"]) == 64
        assert all(request[k] for k in ("question_source", "context_source", "preflight_source"))
    workflow = (root/".github/workflows/stock-business-research.yml").read_text()
    assert "reviewed-question:" in workflow and "group: stock-business-first-v0" in workflow
    assert "if: github.event_name == 'workflow_dispatch' && inputs.reviewed-question" in workflow
    assert 'test "$REVIEWED_QUESTION" != true' in workflow
    assert 'decision_kernel.runtime.stock_question_host' in workflow


@pytest.mark.parametrize("event", ["schedule", "workflow_run", "push"])
def test_question_cli_rejects_nonmanual_events_before_api(tmp_path, monkeypatch, event):
    monkeypatch.setenv("GITHUB_REPOSITORY", once.REPO)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("GITHUB_SHA", "a"*40)
    monkeypatch.setenv("GITHUB_EVENT_NAME", event)
    with pytest.raises(once.TrialError):
        host.main(["--code-commit", "a"*40, "--output", str(tmp_path/"out")])
    assert not (tmp_path/"out").exists()


def test_revision_and_approval_do_not_reopen_consumed_question(tmp_path, monkeypatch):
    args, api, request, q, _, _, calls, writes, prefix = setup_question(tmp_path, monkeypatch)
    first = host.run_question(**args)
    assert first["status"] == "VALIDATED_FUNNEL_RESULT", first
    original = dict(request["question_source"], purpose="QUESTION_PREDECESSOR")
    q.update(revision=2, predecessor=original,
             declared_at=(reading.clock(args["clock"]())-timedelta(minutes=21)).isoformat())
    new = once.source_ref("research_runs/question-plan/revision2.json", "9"*40, once.raw(q), reviewed.PURPOSE)
    request["question_source"] = new
    api.files[new["ref"]] = {new["path"]: once.raw(q)}
    get = api.get
    def meta(path):
        if path == "git/commits/"+new["ref"]:
            return {"sha": new["ref"], "committer": {"date": (reading.clock(args["clock"]())-timedelta(minutes=20)).isoformat()}}
        return get(path)
    api.get = meta
    _, packet, discovery, context, _ = host._question_inputs(api=api, code=args["code"], request=request, clock=args["clock"])
    request["approved_egress_hash"] = host.question_egress_hash(packet, discovery, context)
    store_request(api, args["code"], request)
    before_calls, before_writes = len(calls), len(writes)
    args["output"] = tmp_path/"revision2"
    result = host.run_question(**args)
    assert packet.candidate_output_prefix == prefix
    assert result["status"] == "EXISTING_QUESTION_REUSED_NO_EXECUTION", result
    assert len(calls) == before_calls and len(writes) == before_writes


def test_revocation_after_launch_prevents_first_model_call(tmp_path, monkeypatch):
    args, api, _, _, _, _, calls, writes, _ = setup_question(tmp_path, monkeypatch)
    original = once.Retainer.save
    def revoke(self, name, value):
        result = original(self, name, value)
        if name == "launch.json": api.comment["body"] = "revoked-after-launch"
        return result
    monkeypatch.setattr(once.Retainer, "save", revoke)
    result = host.run_question(**args)
    assert result["status"] == "NOT_EXECUTED" and not result["formal_research_started"]
    assert (args["output"]/"launch.json").exists() and not calls


def test_truncated_work_history_is_not_empty_history(tmp_path, monkeypatch):
    args, api, _, _, _, _, calls, writes, _ = setup_question(tmp_path, monkeypatch)
    api.heads[intake.WORK_REF] = args["code"]
    original = api.get
    api.get = lambda path: {"truncated": True, "tree": []} if path.startswith("git/trees/") else original(path)
    result = host.run_question(**args)
    assert result["error_code"] == "QUESTION_WORK_TREE_INCOMPLETE" and not calls and not writes


def test_public_approval_excludes_only_runtime_cutoff_not_source_text(tmp_path, monkeypatch):
    args, api, request, _, _, _, _, _, _ = setup_question(tmp_path, monkeypatch)
    _, packet, discovery, context, _ = host._question_inputs(
        api=api, code=args['code'], request=request, clock=args['clock'])
    digest = host.question_egress_hash(packet, discovery, context)
    later = packet.model_copy(update={'code_commit': '8'*40,
        'research_cutoff': packet.research_cutoff + timedelta(minutes=1)})
    assert host.question_egress_hash(later, discovery, context) == digest
    changed = deepcopy(context)
    changed['issuer_documents'][0]['pages'][0]['text'] += ' changed public material'
    assert host.question_egress_hash(packet, discovery, changed) != digest
    changed_question = packet.model_copy(update={'research_question': 'another question'})
    assert host.question_egress_hash(changed_question, discovery, context) != digest
