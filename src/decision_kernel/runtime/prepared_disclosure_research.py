"""Run one explicitly authorized, already prepared saved disclosure input.

THIN_ADAPTER: reuse the original reservation, admission, Pre/Quick and Retainer.
No CLI, source fetch, discovery selector, scheduler, automatic promotion or retry.
The trusted caller owns source preparation, public-egress approval and runtime
limits; an arbitrary source document or a saved admission PASS is not authority.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..identity import canonical_hash
from ..research_funnel import DiscoveryInput
from . import external_research_admission as admission
from . import external_research_identity as identity
from . import incremental_disclosure as work
from . import saved_research_once as once
from .current_state_delivery import GitHubReadError
from .external_research_execution import ExternalResearchInputPacket

DISCOVERY_PURPOSE = "PREPARED_DISCLOSURE_DISCOVERY"


def public_egress_hash(packet, discovery, context) -> str:
    """Bind all prepared prompt material, not provider wire bytes or consent.

    The operator supplies an independently approved digest to run_prepared.
    This helper does not approve its own output. Source refs/authorization prose
    are not sent to the model by the existing research loop.
    """
    return canonical_hash({"input_hash": canonical_hash(packet),
                           "discovery": discovery.model_dump(mode="json"),
                           "public_context": context})


def _one(packet, purpose):
    sources = [s.model_dump(mode="json") for s in packet.source_refs if s.purpose == purpose]
    once.require(len(sources) == 1, "prepared source purpose missing or ambiguous")
    return sources[0]


def _supported(packet, discovery, context, context_source, reserved) -> None:
    once.require(packet.source_lane == "CNINFO_INCREMENTAL" and packet.ticker in work.SCOPE
                 and packet.ticker == reserved.stock_code, "outside approved disclosure scope")
    once.require(packet.untrusted_test_material is None, "test material is not live context")
    # research() currently accounts for one bundle using the first seed. Do not
    # silently claim arbitrary multi-seed/source support or wider Evidence breadth.
    once.require(len(packet.seed_evidence_artifacts) == 1, "one context seed required")
    seed = packet.seed_evidence_artifacts[0]
    once.require(seed.content_hash == context_source["sha256"] == once.sha(once.raw(context))
                 and seed.source_locator == once.locator(context_source), "context seed differs")
    once.require((discovery.ticker, discovery.security_id, discovery.source_lane, discovery.as_of)
                 == (packet.ticker, packet.security_id, packet.source_lane, packet.research_cutoff),
                 "prepared discovery identity differs")
    once.require(len(discovery.source_lineage) == 1
                 and discovery.source_lineage[0].evidence_artifact_id == seed.id
                 and discovery.source_lineage[0].source_locator == seed.source_locator
                 and discovery.source_lineage[0].available_at == seed.available_at,
                 "prepared discovery lineage differs")
    budget = packet.budget
    once.require(set(packet.allowed_tools) == {"OTHER_READ"}
                 and budget.max_search_queries == budget.max_technical_retries == 0
                 and 3 <= budget.max_tool_calls <= 6 and 3 <= budget.max_source_reads <= 4
                 and budget.max_elapsed_minutes == 15, "unsupported saved executor budget")
    once.require(all(value == "SOFT_EXECUTOR" for key, value in budget.model_dump(mode="json").items()
                     if key.endswith("_enforcement")), "hard enforcement not established by adapter")
    once.require(len(once.raw(context)) < once.MAX_PROMPT_BYTES - 16000,
                 "context exceeds saved executor bound; no clipping")


def run_prepared(*, api, code_commit: str, input_source: dict, expected_key: dict,
                 approved_egress_hash: str, output: Path,
                 clock: Callable[[], str] = once.now, call=None) -> dict:
    """Consume one exact prepared input; create-only launch precedes fresh admission.

    api is the existing bounded GitHub client. call is an offline test seam;
    production uses the existing pinned model_call, never a source-named callable.
    This is not a daily entry: no production workflow invokes it in this slice.
    """
    once.require(not output.is_symlink() and not any(p.is_symlink() for p in output.parents),
                 "unsafe local output")
    output.mkdir(parents=True, exist_ok=False)
    host = {"status": "NOT_EXECUTED", "phase": "PREPARED_INPUT", "started_at": clock(),
            "formal_research_started": False, "code_commit": code_commit,
            "automatic_retry": False, "investment_authority": "NONE",
            "semantic_acceptance": "NOT_ESTABLISHED", "current_state_published": False}
    retain = None
    launched = False
    current = lambda: api._call("GET", "git/ref/heads/main").json()["object"]["sha"]
    load = lambda s: api.file(s["path"], s["ref"])
    try:
        once.require(current() == code_commit, "main moved")
        data = identity._checked_source(input_source, load)
        packet = ExternalResearchInputPacket.model_validate(identity._json(data))
        once.require(packet.code_commit == code_commit
                     and identity.input_key(packet).as_dict() == expected_key, "prepared input differs")
        packet_source = _one(packet, work.PACKET_PURPOSE)
        reserved_raw = identity._checked_source(packet_source, load)
        reserved = work._packet(reserved_raw)
        prefix = work.request_path(reserved.assessment_input_hash).removesuffix("packet.json")
        once.require(packet_source["path"] == prefix + "packet.json"
                     and packet.candidate_output_prefix == prefix
                     and input_source["path"] == prefix + "input.json", "prepared reservation differs")
        work_head = api._call("GET", "git/ref/heads/" + work.WORK_REF).json()["object"]["sha"]
        once.require(api.file(packet_source["path"], work_head) == reserved_raw,
                     "packet is not reserved on the existing work ref")
        try:
            api.file(prefix + "launch.json", work_head)
        except GitHubReadError as exc:
            if str(exc) != "GitHub HTTP 404":
                raise
        else:
            host["status"] = "ALREADY_LAUNCHED_NO_EXECUTION"
            return host
        context_source = _one(packet, "MODEL_CONTEXT")
        context = identity._json(identity._checked_source(context_source, load))
        discovery = DiscoveryInput.model_validate(identity._json(
            identity._checked_source(_one(packet, DISCOVERY_PURPOSE), load)))
        once.require(context.get("disclosure_packet") == identity._json(reserved_raw),
                     "public context changed the reserved disclosure")
        once.require(reserved.prepared_at <= packet.selected_at, "reserved packet is from the future")
        discovery_ref = _one(packet, DISCOVERY_PURPOSE)["ref"]
        discovery_meta = api.get("git/commits/" + discovery_ref)
        once.require(discovery_meta["sha"] == discovery_ref
                     and admission.clock(discovery_meta["committer"]["date"]) <= packet.research_cutoff,
                     "prepared discovery is from the future")
        _supported(packet, discovery, context, context_source, reserved)
        once.require(public_egress_hash(packet, discovery, context) == approved_egress_hash,
                     "public egress not approved for these exact inputs")
        preflight = identity._checked_source(_one(packet, admission.PREFLIGHT_PURPOSE), load)
        catalogue = api.file(identity.CATALOG_PATH, code_commit)
        checks = dict(input_raw=data, preflight_raw=preflight,
            catalog_source=once.source_ref(identity.CATALOG_PATH, code_commit, catalogue,
                                          "CURRENT_CODE_EXECUTION_SCOPE"),
            input_source=input_source, expected_key=expected_key, load=load,
            commit=lambda ref: api.get("git/commits/" + ref), current_code=current,
            checked_at=clock(), now=clock)
        # Reject bad/expired preparation before any remote mutation. The second
        # check below is still mandatory after launch marker write/readback.
        preliminary = admission.assess_admission(**checks)
        if not preliminary["research_execution_allowed"]:
            host["reason"] = preliminary["reason"]
            (output / "admission.json").write_bytes(once.raw(preliminary))
            return host
        retain = once.Retainer(api, {"prefix": prefix, "id": packet.execution_id,
                                    "work_ref": work.WORK_REF}, code_commit, output)
        host.update(phase="LAUNCH_RESERVATION", execution_key=expected_key,
                    input_source=input_source, approved_egress_hash=approved_egress_hash)
        # No previous SHA: a competing/existing marker rejects repeat spending.
        retain.save("launch.json", {"id": packet.execution_id, "input_hash": canonical_hash(packet),
            "code_commit": code_commit, "started_at": clock(), "automatic_retry": False,
            "approved_egress_hash": approved_egress_hash})
        launched = True
        checks["checked_at"] = clock()

        def execute(exact, key):
            once.require(exact == data and key == expected_key, "callback identity differs")
            host.update(phase="RESEARCH", formal_research_started=True)
            return once.research(packet, discovery, context, output, call=call, clock=clock)

        report, executed = admission.execute_after_admission(executor=execute, **checks)
        host["phase"] = "RETENTION"
        retain.save("admission.json", report)
        if executed is None:
            host["reason"] = report["reason"]
            return host
        candidate, result, _usage = executed
        # Reuse the original disclosure-to-output binding, not a new route rule.
        work.describe_outcome(reserved_packet=reserved_raw, input_raw=data,
                              candidate_raw=once.raw(candidate))
        retain.save("candidate.json", candidate)
        retain.save("receipt.json", candidate.receipt)
        retain.save("validation.json", result)
        if result.funnel_result is not None:
            retain.save("funnel.json", result.funnel_result)
        text = (f"# {packet.ticker} 保存公告研究候选（未语义验收）\n\n"
                f"问题：{packet.research_question}\n\n原验证器：{result.status.value}\n")
        if result.funnel_result is not None:
            text += f"\n原处置：{result.funnel_result.terminal_state.value}\n"
        text += "\n原输入和证据范围不扩张。未自动登记、发布、Deep、Belief/Odds更新或投资决定。\n"
        retain.save("README.md", text.encode())
        host.update(status=result.status.value, phase="COMPLETE",
                    candidate_hash=canonical_hash(candidate), validation_hash=canonical_hash(result))
    except Exception as exc:
        host.update(status="EXECUTION_INCOMPLETE" if host["formal_research_started"] else "NOT_EXECUTED",
                    error_type=type(exc).__name__)
        if isinstance(exc, (once.TrialError, identity.ExecutionIdentityError)):
            host["error_code"] = exc.code
        # Do not echo untrusted exceptions, compensate writes, reset a marker or retry.
    finally:
        host.update(finished_at=clock(), mutation_uncertain=bool(retain and retain.uncertain),
                    retained_files=list(retain.writes) if retain else [])
        if launched and retain is not None and not retain.uncertain:
            try:
                retain.save("host-receipt.json", host)
            except Exception as exc:
                host.update(status="RETENTION_INCOMPLETE", error_type=type(exc).__name__,
                            mutation_uncertain=retain.uncertain)
                (output / "host-retention-failure.json").write_bytes(once.raw(host))
        else:
            (output / "host-receipt.json").write_bytes(once.raw(host))
    return host
