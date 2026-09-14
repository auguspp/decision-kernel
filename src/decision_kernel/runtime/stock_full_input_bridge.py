"""Compose full Stock inputs with the ORIGINAL capture, Retainer and SDK executor.

This is internal opt-in, not a dispatch mode or a successor/permission issuer.
No alternative Research loop, source clock, Evidence ID or global byte limit.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import re

from . import saved_research_once as once
from . import stock_full_input as full


@dataclass(frozen=True)
class BoundFullContext:
    """Stored and decoded identities, not execution authority; exact bytes only."""
    ticker: str
    source_raw: bytes
    stored_raw: bytes
    decoded_raw: bytes
    pre_prompt_sha256: str | None = None
    pre_request_sha256: str | None = None

    @classmethod
    def load(cls, spec, load, *, ticker):
        captured = []
        def checked_load(source):
            data = load(source)
            captured.append(data)
            return data
        decoded = full.checked_unpack(spec, checked_load, ticker=ticker)
        once.require(len(captured) == 1, "full input source read count differs")
        return cls(ticker, once.raw(spec), captured[0], decoded)

    def source(self):
        return once.identity._json(self.source_raw)

    def check_plain(self, context):
        # Recheck even a directly constructed instance; dataclass construction
        # is not proof that the original checked-source/decoder ran.
        decoded = full.checked_unpack(self.source(), lambda _: self.stored_raw, ticker=self.ticker)
        once.require(decoded == self.decoded_raw == once.raw(context), "full input plain context changed")

    def check_packet(self, packet, context):
        from . import stock_research_intake as intake
        self.check_plain(context)
        specs = [s.model_dump(mode="json") for s in packet.source_refs if s.purpose == "MODEL_CONTEXT"]
        once.require(packet.ticker == self.ticker and packet.source_lane == intake.LANE
            and packet.security_id == intake.security(context["stock_observation"]["row"]["thscode"])
            and specs == [self.source()], "full input packet source binding differs")
        once.require(any(e.content_hash == once.sha(self.stored_raw)
            and e.raw_storage_ref == once.locator(self.source()) for e in packet.seed_evidence_artifacts),
            "full input seed is not bound to stored source")

    def recheck(self, load):
        fresh = type(self).load(self.source(), load, ticker=self.ticker)
        once.require(fresh.stored_raw == self.stored_raw and fresh.decoded_raw == self.decoded_raw,
                     "full input retained source changed")

    def record(self):
        return {"policy": full.POLICY, "stored_bytes": len(self.stored_raw),
            "stored_sha256": once.sha(self.stored_raw), "decoded_bytes": len(self.decoded_raw),
            "decoded_sha256": once.sha(self.decoded_raw)}

    def prepared(self, preview):
        once.require(preview["decoded_sha256"] == once.sha(self.decoded_raw)
            and preview["meaning"] == "SDK_PRE_REQUEST_BUILT_NO_NETWORK_NOT_ADMISSION"
            and all(isinstance(preview[k], str) and re.fullmatch(r"[0-9a-f]{64}", preview[k])
                    for k in ("prompt_sha256", "request_sha256")), "full input Pre preview differs")
        return replace(self, pre_prompt_sha256=preview["prompt_sha256"],
                       pre_request_sha256=preview["request_sha256"])

    def request_check(self, stage, prompt, output_type, parameters):
        once.require((stage, output_type) in {("pre", once.PreResearchResult), ("quick", once.QuickResearchResult)}
            and prompt["stage"] == stage.upper(), "full input original stage differs")
        self.check_plain(prompt["public_context"])
        return full.FinalRequestCheck.build(self.decoded_raw, ticker=self.ticker,
            expected_url=once.BASE_URL + "/responses", parameters={**parameters, "stream": True})

    def send_hook(self, stage, prompt, output_type, parameters, receipt):
        once.require(self.pre_request_sha256 is not None and self.pre_prompt_sha256 is not None,
                     "full input missing pre-launch SDK preview")
        if stage == "pre":
            once.require(once.sha(once.raw(prompt)) == self.pre_prompt_sha256,
                         "full input Pre prompt changed after preview")
        check = self.request_check(stage, prompt, output_type, parameters).hook(receipt)
        def hook(request):
            check(request)
            if stage == "pre":
                once.require(receipt["request_sha256"] == self.pre_request_sha256,
                             "full input actual Pre request changed after preview")
        return hook


def require_bound(value):
    once.require(type(value) is BoundFullContext, "full input requires explicit bound context")
    return value


def successor_prompt_context(packet, context, bound):
    """Describe bound input/lineage scopes; never attest admission or a route.

    Called by the SAME Pre builder for SDK preview and actual execution. Quick
    inherits that prompt only after the original validated Pre transition.
    No context mutation, network, source-truth check or new execution identity.
    """
    require_bound(bound).check_packet(packet, context)
    history = context.get("source_successor")
    if "source_successor" not in context:
        return {}  # Preserve unrelated/default full-input prompts byte-for-byte.
    once.require(isinstance(history, dict)
        and isinstance(history.get("current_reading"), dict)
        and isinstance(history.get("successor_request"), dict)
        and history.get("execution_id") == packet.execution_id
        and history.get("prefix") == packet.candidate_output_prefix
        and history.get("thscode") == context["stock_observation"]["row"]["thscode"]
        and history.get("current_reading", {}).get("ref") == packet.current_state_commit
        and history.get("successor_request", {}).get("ref") == packet.code_commit,
        "full input successor prompt identity differs")
    inventory = context["issuer_inventory"]
    return {"source_state_interpretation": {
        "contract": "STOCK_SUCCESSOR_FIELD_SCOPES_V1",
        "current_request": {"execution_id": packet.execution_id,
            "code_commit": packet.code_commit,
            "reading_commit": packet.current_state_commit,
            "context_sha256": once.sha(bound.decoded_raw),
            "meaning": "REQUEST_INPUT_IDENTITY_NOT_EXECUTION_STATUS"},
        "supplied_material": {
            "selected_ids": list(inventory["selected_ids"]),
            "document_count": len(context["issuer_documents"]),
            "page_count": sum(d["page_count"] for d in context["issuer_documents"]),
            "meaning": "PRESENT_BOUND_REPRESENTATIONS_NOT_TRUTH_OR_ADMISSION"},
        "historical_fields": {
            "public_context.source_successor.current_reading_item_status":
                "INHERITED_PREDECESSOR_SNAPSHOT_NOT_CURRENT_EXECUTION_STATUS",
            "public_context.source_successor.material":
                "SAVED_SOURCE_ONLY_PREPARATION_SNAPSHOT_NOT_CURRENT_INPUT_GAPS"},
        "rules": (
            "The source_successor object mixes current child bindings with historical lineage; "
            "do not treat the entire object as either current state or obsolete data. "
            "In particular, material.missing_page_reviews records OLD missing pages, when present. "
            "Compare them with the supplied issuer_documents pages and their exact review_source "
            "before claiming a page is currently absent. Do not erase or reinterpret old failures. "
            "The current request is not a completed stage; prompt construction does not attest "
            "admission, delivery or Research completion. Only the original host/admission and "
            "execution receipts establish those technical states. Do not infer this invocation "
            "failed from a predecessor PRE_EXECUTION_FAILURE. "
            "Use business evidence for the existing route choices; no route is forced. "
            "Supplementary market/customer/competitor information outside the declared required "
            "source classes may remain UNKNOWN; that is not itself a technical failure or a "
            "new mandatory Deep requirement. Genuine current required-source or execution gaps "
            "must still not be disguised as completed WAIT or a business rejection.")
    }}


def capture_complete(**kwargs):
    """Use original whole-source preparation, never clip or recapture on failure."""
    from . import stock_research_sources as sources
    ticker, output = kwargs["ticker"], kwargs["output"]
    once.require(ticker in full.TICKERS, "full input capture outside repair scope")
    prepared = sources.capture(**kwargs, preparation_only=True)
    once.require(prepared["all_planned_bodies_inspected"] is True
        and prepared["inventory_checked"] is True and prepared["unattempted_ids"] == []
        and prepared["missing_page_reviews"] == []
        and prepared["selected_ids"] == prepared["checked_body_ids"]
        and prepared["complete_context"] is not None,
        "full input source preparation incomplete")
    spec = prepared["complete_context"]
    once.require(spec["path"] == "prepared-context.json", "full input prepared path differs")
    path = output / spec["path"]
    once.require(not path.is_symlink() and path.is_file() and path.stat().st_size <= full.DECODED_BYTES,
                 "full input prepared context bound")
    with path.open("rb") as stream:
        data = stream.read(full.DECODED_BYTES + 1)
    once.require(len(data) == spec["bytes"] and once.sha(data) == spec["sha256"],
                 "full input prepared context identity differs")
    context = full._context(data, ticker)
    once.require(context["issuer_inventory"]["selected_ids"] == prepared["selected_ids"]
        and once.sha(once.raw(context["issuer_inventory"])) == prepared["inventory_sha256"],
        "full input prepared inventory differs")
    packed = full.pack(data, ticker=ticker)
    journal_path = output / "source-journal.json"
    once.require(not journal_path.is_symlink() and journal_path.is_file()
        and journal_path.stat().st_size <= once.identity.MAX_BYTES, "full input journal bound")
    with journal_path.open("rb") as stream:
        journal = once.identity._json(stream.read(once.identity.MAX_BYTES + 1))
    reads = journal["completed_reads"]
    once.require([r["identity"] for r in reads] == [ticker + ":" + i for i in prepared["selected_ids"]],
                 "full input prepared reads differ")
    sources.recheck(context, api=kwargs["api"], code_commit=kwargs["code_commit"], clock=kwargs["clock"])
    with (output / "full-input-preparation.json").open("xb") as stream:
        stream.write(once.raw({"status": "COMPLETE_SOURCE_REPRESENTATION_NOT_EXECUTION_ADMISSION",
            "original_preparation_status": prepared["status"], "decoded_bytes": len(data),
            "decoded_sha256": once.sha(data), "stored_bytes": len(packed), "stored_sha256": once.sha(packed)}))
    return context, reads, {"started_at": journal["started_at"], "finished_at": journal["finished_at"],
        "inventory_finished_at": context["issuer_inventory"]["checked_at"],
        "decoded_query_events": journal["events"], "scope": journal["scope"],
        "captured_pdf_bytes": journal["captured_pdf_bytes"]}


def preview_pre(packet, discovery, context, bound):
    """Build the EXACT current Pre HTTP request with the original SDK, NO network.

    No fake future Quick, model output or launch; supplied clocks/IDs unchanged.
    The fake transport always rejects, including if the request hook is bypassed.
    """
    from openai import OpenAI, DefaultHttpxClient
    require_bound(bound).check_packet(packet, context)
    prompt = once.pre_prompt(packet, discovery, context, bound_context=bound)
    _, _, _, parameters = once.model_request(prompt, once.PreResearchResult, max_prompt_bytes=full.REQUEST_BYTES)
    record = {}
    check = bound.request_check("pre", prompt, once.PreResearchResult, parameters).hook(record)
    class PreparedLocally(BaseException):
        pass  # Deliberately not an SDK-retryable Exception.
    def inspect(request):
        check(request)
        raise PreparedLocally()
    class NoNetwork:
        def __enter__(self): return self
        def __exit__(self, *args): self.close()
        def close(self): pass
        def handle_request(self, request):
            raise once.TrialError("full input preview reached forbidden transport")
    with OpenAI(api_key="local-preview-not-a-credential", base_url=once.BASE_URL, max_retries=0,
        http_client=DefaultHttpxClient(transport=NoNetwork(), follow_redirects=False,
            trust_env=False, event_hooks={"request": [inspect]})) as client:
        try:
            with client.responses.stream(**parameters) as stream:
                stream.get_final_response()
        except PreparedLocally:
            pass
        else:
            raise once.TrialError("full input preview unexpectedly returned")
    once.require(bool(record), "full input preview did not check request")
    return {**record, "prompt_sha256": once.sha(once.raw(prompt)),
            "meaning": "SDK_PRE_REQUEST_BUILT_NO_NETWORK_NOT_ADMISSION"}
