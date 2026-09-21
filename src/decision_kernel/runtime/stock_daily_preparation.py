"""Assemble a DISABLED daily request from saved review/custody/preflight.

Only the existing host can authorize, reserve or execute Research. This command
uses its original preparation functions, not a second admission implementation.
It neither acquires issuer material nor manufactures a question or source receipt.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import os
from pathlib import Path
import re

SELECTORS = ("batch_review", "source_custody", "preflight")
SUCCESS = "DAILY_INPUT_DRAFT_VERIFIED_NOT_EXECUTABLE"


def selector(value: str) -> dict:
    """CLI convenience only; not a new persisted Kernel/source schema."""
    ref, separator, path = value.partition(":")
    if (not separator or re.fullmatch(r"[0-9a-f]{40}", ref) is None
            or re.fullmatch(r"[A-Za-z0-9_./-]{1,512}", path) is None or path.startswith("/")
            or "\\" in path or any(p in {"", ".", ".."} for p in path.split("/"))):
        raise ValueError("DAILY_PREPARATION_EXACT_SELECTOR_REQUIRED")
    return {"ref": ref, "path": path}


class ReadOnlyGit:
    """Expose only the existing bounded reader operations to preparation."""
    def __init__(self, api):
        self._api = api

    def _call(self, method, path, *args, **kwargs):
        if method != "GET":
            raise ValueError("DAILY_PREPARATION_READ_ONLY")
        return self._api._call(method, path, *args, **kwargs)

    def get(self, path):
        return self._api.get(path)

    def file(self, path, ref):
        return self._api.file(path, ref)

    def archive(self, artifact):
        return self._api.archive(artifact)


def assemble(api, selectors: dict) -> dict:
    """Derive five original SourceRefs from three exact saved entry points."""
    from . import external_research_admission as admission
    from . import external_research_identity as identity
    from . import saved_research_once as once
    from . import stock_daily_question as daily
    once.require(isinstance(selectors, dict) and set(selectors) == set(SELECTORS),
                 "DAILY_PREPARATION_SELECTORS_REQUIRED")
    specs, values = {}, {}
    purposes = {"batch_review": daily.EXTRA_SOURCES["batch_review_source"],
                "source_custody": daily.EXTRA_SOURCES["source_custody_source"],
                "preflight": admission.PREFLIGHT_PURPOSE}
    for name in SELECTORS:
        selected = selectors[name]
        once.require(isinstance(selected, dict) and set(selected) == {"ref", "path"}
                     and all(isinstance(v, str) for v in selected.values()),
                     "DAILY_PREPARATION_SELECTOR_SHAPE")
        once.require(selector(selected["ref"] + ":" + selected["path"]) == selected,
                     "DAILY_PREPARATION_EXACT_SELECTOR_REQUIRED")
        raw = api.file(selected["path"], selected["ref"])
        once.require(isinstance(raw, bytes) and len(raw) <= identity.MAX_BYTES,
                     "DAILY_PREPARATION_SOURCE_SIZE")
        specs[name] = once.source_ref(selected["path"], selected["ref"], raw, purposes[name])
        values[name] = identity._json(raw)
    return {"schema_version": 1, "enabled": False, "mode": daily.MODE,
            "permission": deepcopy(daily.PERMISSION),
            "question_source": deepcopy(values["batch_review"]["question_source"]),
            "context_source": deepcopy(values["source_custody"]["context"]),
            "preflight_source": specs["preflight"],
            "batch_review_source": specs["batch_review"],
            "source_custody_source": specs["source_custody"],
            "approved_egress_hash": None}


def prepare(*, api, code: str, selectors: dict, output: Path, clock=None) -> dict:
    """Original gates, zero spend/writes to Git; success exports disabled data.

    Question authoring and real source custody must already exist. A successful
    preview cannot replace the host's current-main authorization or launch checks.
    """
    from . import current_state as reading
    from . import external_research_identity as identity
    from . import reviewed_question_input as reviewed
    from . import research_commit_only as retained
    from . import saved_research_once as once
    from . import stock_daily_question as daily
    from . import stock_question_continuation as deepseek
    from . import stock_question_host as host
    from . import stock_research_sources as sources
    clock = clock or once.now
    once.require(not output.exists() and not output.is_symlink()
                 and not any(p.is_symlink() for p in output.parents),
                 "DAILY_PREPARATION_CREATE_ONLY_OUTPUT")
    output.mkdir(parents=True, exist_ok=False)
    api = ReadOnlyGit(api)
    report = {"status": "DAILY_INPUT_PREPARATION_GAP", "phase": "ASSEMBLY",
              "code_commit": code, "started_at": clock(), "request_draft_written": False,
              "remote_writes": 0, "model_calls": 0, "source_site_requests": 0,
              "daily_slots_consumed": 0, "research_execution_allowed": False,
              "permission_status": "NOT_GRANTED_BY_PREPARATION", **reading.AUTHORITY}
    try:
        once.require(isinstance(code, str) and reading.SHA.fullmatch(code)
                     and host.head(api, "main") == code, "DAILY_PREPARATION_MAIN_CHANGED")
        request = assemble(api, selectors)
        daily.check_policy(api, code, request, clock)
        report["phase"] = "ORIGINAL_INPUT_PREPARATION"
        q, packet, discovery, context, checks = host._question_inputs(
            api=api, code=code, request=daily.base_request(request), clock=clock)
        packet, state, scope = daily.bind(api, request, q, packet, context, clock)
        checks = {**checks, "input_raw": once.raw(packet)}
        prepared = reviewed.prepare(question_source=request["question_source"],
                                    checked_at=clock(), **checks)
        sources.recheck(context, api=api, code_commit=code, clock=clock)
        report["phase"] = "UNCONSUMED_SCOPE_AND_REQUEST_PREVIEW"
        work, rows = daily.work_tree(api)
        once.require(not any(p.startswith(packet.candidate_output_prefix) for p in rows),
                     "DAILY_PREPARATION_QUESTION_ALREADY_CONSUMED")
        daily.capacity(api, work, rows, state, packet)
        scope.update(execution_id=packet.execution_id, question_source=request["question_source"])
        daily.reservation_plan(api, work, rows, scope)
        deepseek._deepseek_request(once.pre_prompt(packet, discovery, context), once.PreResearchResult)
        preview_hash = deepseek.egress_hash(packet, discovery, context)
        once.require(host.head(api, "main") == code and daily.work_tree(api)[0] == work,
                     "DAILY_PREPARATION_STATE_CHANGED")
        pf = identity._json(checks["preflight_raw"])
        until = min(reading.clock(pf["valid_until"]), reading.clock(state["checks"]["recheck_after"]),
                    reading.clock(daily.POLICY["execute_before"]))
        once.require(reading.clock(clock()) < until, "DAILY_PREPARATION_WINDOW_EXPIRED")
        # The only request produced is disabled. Nothing is registered or launched.
        retained._write(output / "request.json", once.raw(request))
        report.update(status=SUCCESS, phase="COMPLETE", request_draft_written=True,
                      request_sha256=once.sha(once.raw(request)), execution_id=packet.execution_id,
                      question_id=q["question_id"], case_id=packet.case_id,
                      market_session=scope["market_session"], batch_id=scope["batch_id"],
                      reading_commit=packet.current_state_commit, work_commit=work,
                      context_bytes=len(once.raw(context)), pdf_bytes=scope["pdf_bytes"],
                      original_preparation=prepared, preview_egress_hash=preview_hash,
                      recheck_before=until.isoformat(),
                      meaning="DISABLED_DRAFT_FOR_REVIEW_NOT_AUTHORIZATION_OR_LAUNCH_TOKEN")
    except (ValueError, KeyError, TypeError, AttributeError, OSError, RuntimeError) as exc:
        code_value = getattr(exc, "code", None)
        report.update(status="DAILY_INPUT_PREPARATION_GAP", error_type=type(exc).__name__,
                      error_code=(code_value if isinstance(code_value, str)
                                  and re.fullmatch(r"[A-Z0-9_]{1,128}", code_value)
                                  else "DAILY_INPUT_PREPARATION_REJECTED"))
    report["finished_at"] = clock()
    retained._write(output / "preparation.json", once.raw(report))
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-commit", required=True)
    for name in SELECTORS:
        parser.add_argument("--" + name.replace("_", "-"), type=selector, required=True,
                            metavar="COMMIT:PATH")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    from .current_state_delivery import GitHubAPI
    from . import saved_research_once as once
    report = prepare(api=GitHubAPI(os.environ["GH_TOKEN"], max_calls=1024),
                     code=args.code_commit, output=args.output,
                     selectors={name: getattr(args, name) for name in SELECTORS})
    print(once.raw(report).decode())
    return 0 if report["status"] == SUCCESS else 2


if __name__ == "__main__":
    raise SystemExit(main())
