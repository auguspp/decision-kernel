"""Stock-to-Research selection and stable first-business-question identities.

THIN_ADAPTER: consume the original validated Stock artifact, not another price
screen. This is selection, not Research, Human attention or investment authority.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..identity import canonical_hash
from . import current_state as reading
from . import external_research_identity as identity
from . import saved_research_once as once
from .external_research_execution import (ExternalResearchInputPacket,
    ExternalResearchCandidate, validate_external_research_candidate)

WORK_REF = "research-work/stock-business-v0"
PREFIX = "research_runs/candidates/stock-business/"
LANE = "STOCK_MARKET_EXPRESSION"
QUESTION_KIND = "FIRST_BUSINESS_BASELINE"
CODE = re.compile(r"(?:[036]\d{5})\.(?:SH|SZ)\Z")
QUESTION = ("核验公司主营业务与触发板块的真实联系，收入、利润和现金流如何暴露；"
            "列明支持、反证、替代解释和UNKNOWN。价格强势不证明业务受益，"
            "本次不是全公司Deep、涨价原因认证或投资建议。")


def security(thscode: str) -> str:
    once.require(isinstance(thscode, str) and CODE.fullmatch(thscode) is not None,
                 "unsupported Stock security identity")
    ticker, suffix = thscode.split(".")
    once.require((suffix == "SH") == ticker.startswith("6"), "Stock exchange differs")
    return ("SSE:" if suffix == "SH" else "SZSE:") + ticker


def execution(thscode: str) -> tuple[str, str]:
    sid = security(thscode)
    key = canonical_hash({"security_id": sid, "question_kind": QUESTION_KIND})
    return "stock-business-" + key, PREFIX + key + "/"


def plan(run: dict, files: dict[str, bytes]) -> dict:
    qualified = reading.validate_stock(run, files)
    projection = identity._json(files["reading/stock-reading.json"])["projection"]
    rows = projection["all_stock_observations"]
    once.require(len(rows) == qualified["coverage"]["planned_issuers"]
                 and len({row["thscode"] for row in rows}) == len(rows), "Stock plan coverage differs")
    items, excluded = [], []
    for row in rows:
        thscode = row["thscode"]
        security(thscode)
        if row["eligible_for_shadow_reading"] is not True:
            excluded.append({"thscode": thscode, "company_name": row["company_name"],
                "status": row["status"], "input_failure": row["input_failure"],
                "excluded_reasons": row["excluded_reasons"]})
            continue
        once.require(row["status"] == "CONTRACT_CHECKED_RAW_READING"
                     and row["input_failure"] is None and not row["excluded_reasons"],
                     "qualified Stock row conflicts with its disposition")
        eid, prefix = execution(thscode)
        items.append({"thscode": thscode, "security_id": security(thscode),
            "company_name": row["company_name"], "execution_id": eid, "prefix": prefix,
            "observation": row})
    once.require(len(items) == qualified["coverage"]["qualified_issuers"], "Stock qualified count differs")
    return {"schema_version": 1, "source_run": reading.concise_run(run),
        "market_session": qualified["market_session"], "projection_hash": qualified["projection_hash"],
        "question_kind": QUESTION_KIND, "items": items, "excluded": excluded,
        "selection": "ALL_QUALIFIED_NOT_SURFACED_CARDS", "new_research_result": False,
        **reading.AUTHORITY}


def inventory(api, commit: str) -> dict[str, dict]:
    tree = api.get("git/trees/" + commit + "?recursive=1")
    once.require(tree.get("truncated") is False, "stock work tree incomplete")
    rows = {}
    children = {"source-recovery-v1", "source-successor-v1", "source-successor-continuation-v1"}
    for row in tree["tree"]:
        path = row["path"]
        if not path.startswith(PREFIX) or row["type"] == "tree":
            continue
        parts = path[len(PREFIX):].split("/")
        once.require((len(parts) == 2 or (len(parts) == 3 and parts[1] in children))
                     and re.fullmatch(r"[a-f0-9]{64}", parts[0])
                     and parts[-1] in once.OUTPUT_NAMES and row["type"] == "blob"
                     and row["mode"] == "100644", "stock work path outside contract")
        rows[path] = row
    return rows


def describe(input_raw: bytes, candidate_raw: bytes) -> dict:
    packet = ExternalResearchInputPacket.model_validate(identity._json(input_raw))
    candidate = ExternalResearchCandidate.model_validate(identity._json(candidate_raw))
    thscode = packet.ticker + (".SH" if packet.security_id.startswith("SSE:") else ".SZ")
    root_eid, root_prefix = execution(thscode)
    eid, prefix, work_kind = root_eid, root_prefix, None
    if packet.candidate_output_prefix != root_prefix:
        from .stock_source_recovery import execution as recovery_execution, FAILURE_PURPOSE, SELECTION_PURPOSE
        recovery_eid, recovery_prefix = recovery_execution(thscode)
        if packet.candidate_output_prefix == recovery_prefix:
            parents = {role: [r for r in packet.source_refs if r.purpose == role]
                       for role in (FAILURE_PURPOSE, SELECTION_PURPOSE)}
            once.require(all(len(v) == 1 for v in parents.values())
                and parents[FAILURE_PURPOSE][0].path == root_prefix + "failure.json"
                and parents[SELECTION_PURPOSE][0].path == root_prefix + "prepare.json"
                and packet.research_question == QUESTION, "Stock recovery predecessor binding missing")
            eid, prefix, work_kind = recovery_eid, recovery_prefix, "SOURCE_PREPARATION_RECOVERY"
        else:
            from . import stock_source_successor as successor
            from . import stock_source_successor_continuation as continuation
            successor_eid, successor_prefix = successor.execution(thscode)
            continuation_eid, continuation_prefix = continuation.execution(thscode)
            if packet.candidate_output_prefix == successor_prefix:
                roles = (successor.PARENT_SELECTION_PURPOSE, successor.PARENT_FAILURE_PURPOSE,
                         successor.RECOVERY_SELECTION_PURPOSE, successor.RECOVERY_FAILURE_PURPOSE,
                         successor.REQUEST_PURPOSE, successor.EXPOSURE_PURPOSE)
                refs = {role: [r for r in packet.source_refs if r.purpose == role] for role in roles}
                once.require(all(len(v) == 1 for v in refs.values())
                    and refs[successor.PARENT_SELECTION_PURPOSE][0].path == root_prefix + "prepare.json"
                    and refs[successor.PARENT_FAILURE_PURPOSE][0].path == root_prefix + "failure.json"
                    and refs[successor.RECOVERY_SELECTION_PURPOSE][0].path == recovery_prefix + "prepare.json"
                    and refs[successor.RECOVERY_FAILURE_PURPOSE][0].path == recovery_prefix + "failure.json"
                    and packet.research_question == QUESTION,
                    "Stock successor predecessor/material binding missing")
                eid, prefix, work_kind = successor_eid, successor_prefix, "SOURCE_PREPARATION_SUCCESSOR"
            else:
                once.require(packet.candidate_output_prefix == continuation_prefix,
                             "unknown Stock child execution identity")
                roles = (successor.PARENT_SELECTION_PURPOSE, successor.PARENT_FAILURE_PURPOSE,
                         successor.RECOVERY_SELECTION_PURPOSE, successor.RECOVERY_FAILURE_PURPOSE,
                         continuation.SELECTION_PURPOSE, continuation.FAILURE_PURPOSE,
                         continuation.PREDECESSOR_REQUEST_PURPOSE, continuation.PREDECESSOR_READING_PURPOSE,
                         continuation.REQUEST_PURPOSE, continuation.EXPOSURE_PURPOSE)
                refs = {role: [r for r in packet.source_refs if r.purpose == role] for role in roles}
                once.require(all(len(v) == 1 for v in refs.values())
                    and refs[successor.PARENT_SELECTION_PURPOSE][0].path == root_prefix + "prepare.json"
                    and refs[successor.PARENT_FAILURE_PURPOSE][0].path == root_prefix + "failure.json"
                    and refs[successor.RECOVERY_SELECTION_PURPOSE][0].path == recovery_prefix + "prepare.json"
                    and refs[successor.RECOVERY_FAILURE_PURPOSE][0].path == recovery_prefix + "failure.json"
                    and refs[continuation.SELECTION_PURPOSE][0].path == successor_prefix + "prepare.json"
                    and refs[continuation.FAILURE_PURPOSE][0].path == successor_prefix + "failure.json"
                    and packet.research_question == QUESTION,
                    "Stock successor continuation predecessor/material binding missing")
                eid, prefix, work_kind = continuation_eid, continuation_prefix, "SOURCE_PREPARATION_SUCCESSOR_TECHNICAL_CONTINUATION"
    once.require(packet.source_lane == LANE and packet.execution_id == eid
                 and packet.security_id == security(thscode)
                 and packet.candidate_output_prefix == prefix, "stock research identity differs")
    result = validate_external_research_candidate(packet=packet, candidate=candidate)
    funnel = result.funnel_result
    return {"thscode": thscode, "execution_id": eid, "candidate_output_prefix": prefix,
        **({"work_kind": work_kind, "new_disclosure": False} if work_kind else {}),
        "status": "VALIDATED_FUNNEL_CANDIDATE" if funnel else "VALIDATED_EXECUTION_GAP",
        "completion": result.completion.value, "validation_status": result.status.value,
        "terminal_state": funnel.terminal_state.value if funnel else None,
        "terminal_reason": funnel.terminal_reason if funnel else None,
        "finished_at": candidate.receipt.finished_at.isoformat(),
        "semantic_acceptance": "NOT_ESTABLISHED_BY_READER", "registered_current_handoff": False,
        **reading.AUTHORITY}
