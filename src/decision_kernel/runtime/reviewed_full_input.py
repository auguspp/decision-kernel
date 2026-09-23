"""Complete Industry question input using the existing codec, SDK and host.

Storage compression is lossless; the provider receives the full PLAIN context.
This object binds bytes, not permission, source truth or provider token capacity.
The historical Stock codec/tickers and default small-input path remain separate.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from . import stock_full_input as full
from . import saved_research_once as once
from . import external_research_identity as identity
from . import reviewed_question_input as reviewed
from .stock_full_input_bridge import BoundFullContext

POLICY = "REVIEWED_INDUSTRY_FULL_INPUT_ZLIB_V1"
LIMITS = {"policy": POLICY, "stored_bytes": full.STORED_BYTES,
          "decoded_bytes": full.DECODED_BYTES, "request_bytes": full.REQUEST_BYTES}


def _context(raw, ticker):
    from .disclosure_source_reading import text_ok
    once.require(isinstance(ticker, str) and len(ticker) == 6 and ticker.isascii()
                 and ticker.isdigit(), "FULL_QUESTION_TICKER")
    value = full._json(raw, full.DECODED_BYTES)
    once.require(full._raw(value) == raw and set(value) == {"issuer_documents", "source_limitations"}
                 and text_ok(value["source_limitations"]), "FULL_QUESTION_CONTEXT_SHAPE")
    docs = value["issuer_documents"]
    once.require(isinstance(docs, list) and 0 < len(docs) <= 4
                 and len({d["announcement_id"] for d in docs}) == len(docs),
                 "FULL_QUESTION_DOCUMENT_INVENTORY")
    for doc in docs:
        count, pages = doc["page_count"], doc["pages"]
        once.require(type(count) is int and 0 < count <= 500 and isinstance(pages, list)
                     and len(pages) == count
                     and all(type(p["page_number"]) is int and p["page_number"] == i
                             and text_ok(p["text"]) for i, p in enumerate(pages, 1)),
                     "FULL_QUESTION_PAGE_INVENTORY")
    return value


def pack(raw, *, ticker):
    return full._pack(raw, ticker=ticker, policy=POLICY, check_context=_context)


def unpack(stored, *, ticker):
    return full._unpack(stored, ticker=ticker, policy=POLICY, check_context=_context)


def load_context(spec, load, *, ticker, allowed=False):
    """No automatic large-input fallback; permission opt-in is supplied by host."""
    stored = identity._checked_source(spec, load)
    parsed = identity._json(stored)
    if parsed.get("policy") != POLICY:
        return parsed, None
    once.require(allowed is True, "FULL_QUESTION_INDUSTRY_OPT_IN_REQUIRED")
    bound = ReviewedFullContext.load(spec, lambda _: stored, ticker=ticker)
    return _context(bound.decoded_raw, ticker), bound


def _parameters(prompt, output_type):
    """Same current DeepSeek format adaptation, with the explicit full byte bound."""
    _, _, fmt, _ = once.model_request(prompt, output_type,
        max_prompt_bytes=full.REQUEST_BYTES, model=once.DEEPSEEK_MODEL,
        extra_parameters={"reasoning": {"effort": "none"}})
    once.require(set(fmt) == {"type", "strict", "name", "schema"}
                 and fmt["type"] == "json_schema" and fmt["strict"] is True,
                 "FULL_QUESTION_DEEPSEEK_FORMAT_CHANGED")
    return once.response_parameters(once.raw(prompt).decode(),
        {k: v for k, v in fmt.items() if k != "strict"}, model=once.DEEPSEEK_MODEL,
        extra_parameters={"reasoning": {"effort": "none"}})


@dataclass(frozen=True)
class ReviewedFullContext(BoundFullContext):
    """Reuse original immutable binding and send hook; never the old Stock scope."""
    single_quick_prompt_sha256: str | None = None
    single_quick_request_sha256: str | None = None
    @classmethod
    def load(cls, spec, load, *, ticker):
        once.require(spec.get("purpose") == "MODEL_CONTEXT", "FULL_QUESTION_SOURCE_PURPOSE")
        stored = identity._checked_source(spec, load)
        decoded = unpack(stored, ticker=ticker)
        return cls(ticker, once.raw(spec), stored, decoded)

    def check_plain(self, context):
        stored = identity._checked_source(self.source(), lambda _: self.stored_raw)
        once.require(unpack(stored, ticker=self.ticker) == self.decoded_raw == once.raw(context),
                     "FULL_QUESTION_PLAIN_CONTEXT_CHANGED")

    def check_packet(self, packet, context):
        from .stock_research_intake import security
        self.check_plain(context)
        specs = [s.model_dump(mode="json") for s in packet.source_refs if s.purpose == "MODEL_CONTEXT"]
        once.require(packet.ticker == self.ticker and packet.case_id[:6] == self.ticker
                     and packet.security_id == security(packet.case_id)
                     and packet.source_lane == reviewed.LANE and specs == [self.source()]
                     and any(e.content_hash == once.sha(self.stored_raw)
                             and e.raw_storage_ref == once.locator(self.source())
                             for e in packet.seed_evidence_artifacts), "FULL_QUESTION_PACKET_BINDING")

    def record(self):
        return {**super().record(), "policy": POLICY}

    def request_check(self, stage, prompt, output_type, parameters):
        once.require((stage, output_type) in {("pre", once.PreResearchResult), ("quick", once.QuickResearchResult),
                                              ("quick", once.single_quick.QuickAssessment)}
                     and prompt["stage"] == stage.upper(), "FULL_QUESTION_STAGE")
        self.check_plain(prompt["public_context"])
        expected = _parameters(prompt, output_type)
        once.require(parameters == expected, "FULL_QUESTION_PARAMETERS_CHANGED")
        prepared = full._raw({**parameters, "stream": True})
        once.require(len(prepared) <= full.REQUEST_BYTES, "FULL_QUESTION_REQUEST_TOO_LARGE")
        # The original hook checks actual SDK HTTP bytes, destination and one send.
        return full.FinalRequestCheck(self.decoded_raw, self.ticker,
            once.DEEPSEEK_BASE_URL + "/responses", prepared, policy=POLICY)

    def send_hook(self, stage, prompt, output_type, parameters, receipt):
        if output_type is not once.single_quick.QuickAssessment:
            once.require(self.single_quick_request_sha256 is None
                         and self.single_quick_prompt_sha256 is None,
                         "FULL_QUESTION_LEGACY_PREVIEW_REQUIRED")
            return super().send_hook(stage, prompt, output_type, parameters, receipt)
        once.require(self.single_quick_prompt_sha256 is not None
                     and self.single_quick_request_sha256 is not None
                     and once.sha(once.raw(prompt)) == self.single_quick_prompt_sha256,
                     "FULL_QUESTION_SINGLE_PREVIEW_REQUIRED")
        check = self.request_check(stage, prompt, output_type, parameters).hook(receipt)
        def hook(request):
            check(request)
            once.require(receipt["request_sha256"] == self.single_quick_request_sha256,
                         "FULL_QUESTION_SINGLE_REQUEST_CHANGED")
        return hook

    def egress_hash(self, packet, discovery, context):
        self.check_packet(packet, context)
        if packet.method_version == once.single_quick.METHOD_VERSION:
            prompt = once.initial_prompt(packet, discovery, context)
            prompt["binding"]["as_of"] = "HOST_ASSIGNED_RESEARCH_CUTOFF"
            parameters = _parameters(prompt, once.single_quick.QuickAssessment)
            return once.canonical_hash({"method_version": packet.method_version,
                "prompt_version": packet.prompt_version, "quick_prompt": prompt,
                "full_input": self.record(),
                "source_refs": [s.model_dump(mode="json") for s in packet.source_refs],
                "budget": packet.budget, "endpoint": once.DEEPSEEK_BASE_URL,
                "parameters": {k: v for k, v in parameters.items() if k != "input"},
                "max_model_calls": 1})
        once.require(packet.method_version == "research-funnel-v1", "RESEARCH_METHOD_UNSUPPORTED")
        prompt = once.pre_prompt(packet, discovery, context)
        prompt["binding"]["as_of"] = "HOST_ASSIGNED_RESEARCH_CUTOFF"
        parameters = _parameters(prompt, once.PreResearchResult)
        return once.canonical_hash({"pre_prompt": prompt, "full_input": self.record(),
            "source_refs": [s.model_dump(mode="json") for s in packet.source_refs],
            "budget": packet.budget, "endpoint": once.DEEPSEEK_BASE_URL,
            "parameters": {k: v for k, v in parameters.items() if k != "input"},
            "quick_schema": once.QuickResearchResult.model_json_schema(),
            "quick": "ONLY_ORIGINAL_VALIDATED_PRE_AND_ITS_HASH_ADDED_IF_CONTINUE_TO_QUICK"})

    def preview(self, packet, discovery, context):
        """Real SDK request construction before reservation; transport cannot run."""
        from openai import OpenAI, DefaultHttpxClient
        self.check_packet(packet, context)
        single = packet.method_version == once.single_quick.METHOD_VERSION
        output_type = once.single_quick.QuickAssessment if single else once.PreResearchResult
        prompt = once.initial_prompt(packet, discovery, context)
        parameters = _parameters(prompt, output_type)
        receipt = {}
        check = self.request_check("quick" if single else "pre", prompt, output_type, parameters).hook(receipt)
        class PreparedLocally(BaseException):
            pass
        def inspect(request):
            check(request)
            raise PreparedLocally()
        class NoNetwork:
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
            def close(self): pass
            def handle_request(self, request):
                raise once.TrialError("FULL_QUESTION_PREVIEW_FORBIDDEN_TRANSPORT")
        with OpenAI(api_key="local-preview-not-a-credential", base_url=once.DEEPSEEK_BASE_URL,
            max_retries=0, http_client=DefaultHttpxClient(transport=NoNetwork(),
                follow_redirects=False, trust_env=False, event_hooks={"request": [inspect]})) as client:
            try:
                with client.responses.stream(**parameters) as stream:
                    stream.get_final_response()
            except PreparedLocally:
                pass
            else:
                raise once.TrialError("FULL_QUESTION_PREVIEW_UNEXPECTED_RETURN")
        once.require(bool(receipt), "FULL_QUESTION_PREVIEW_NOT_CHECKED")
        if single:
            return replace(self, single_quick_prompt_sha256=once.sha(once.raw(prompt)),
                           single_quick_request_sha256=receipt["request_sha256"],
                           pre_prompt_sha256=None, pre_request_sha256=None)
        once.require(self.single_quick_request_sha256 is None
                     and self.single_quick_prompt_sha256 is None,
                     "FULL_QUESTION_LEGACY_PREVIEW_REQUIRED")
        return self.prepared({**receipt, "prompt_sha256": once.sha(once.raw(prompt)),
            "meaning": "SDK_PRE_REQUEST_BUILT_NO_NETWORK_NOT_ADMISSION"})


PAGE_REFERENCE = "SAME_PDF_REPLAY_REFERENCE_V1"


def referenced_reading(value):
    return isinstance(value, dict) and value.get("policy") == PAGE_REFERENCE


def replay_loader(api, code, value, clock):
    """Frozen note identity plus current-main equality; never current-main retiming."""
    from . import disclosure_source_reading as pages
    once.require(set(value) == {"policy", "reading_hash", "review_commit"}
        and value["policy"] == PAGE_REFERENCE
        and pages.read.SHA.fullmatch(value["review_commit"])
        and isinstance(value["reading_hash"], str) and len(value["reading_hash"]) == 64
        and all(c in "0123456789abcdef" for c in value["reading_hash"]), "FULL_QUESTION_REPLAY_REFERENCE")
    # Commit metadata is immutable and shared only within this loader. Notes and
    # the mutable main authorization are still read and checked on every re-entry.
    metadata = {}
    class CommitReuse:
        file = staticmethod(api.file)
        @staticmethod
        def get(path):
            if path.startswith("git/commits/"):
                if path not in metadata: metadata[path] = api.get(path)
                return metadata[path]
            return api.get(path)
    prior = pages.main_review_loader(CommitReuse(), value["review_commit"], clock)
    current = pages.main_review_loader(CommitReuse(), code, clock)
    def load(digest, number):
        old, new = prior(digest, number), current(digest, number)
        once.require(old is not None and new is not None and old[0] == new[0],
                     "FULL_QUESTION_TRUSTED_REVIEW_CHANGED")
        return old
    return load


def recheck_pages(context, *, api, code, clock):
    """Preserve original review commit; current main must contain identical notes.

    Checking equal content does not retime a prior review to the new code commit.
    Both exact source read and current trusted-main note/clock checks still run.
    """
    from . import disclosure_source_reading as pages
    current = pages.main_review_loader(api, code, clock)
    for doc in context["issuer_documents"]:
        value = doc.get("page_reading")
        if value is None:
            continue
        if referenced_reading(value):
            replay_loader(api, code, value, clock)  # Full bytes replayed by custody, not a hash-only admission.
            continue
        pages.validate(value, {"pdf_sha256": doc["pdf_sha256"],
            "text_sha256": doc["original_text_sha256"], "page_count": doc["page_count"],
            "source_locator": doc["source_locator"]})
        once.require(doc["pages"] == value["pages"], "FULL_QUESTION_PAGE_READING_CHANGED")
        for page in value["pages"]:
            if page["method"] != "AI_VISUAL_READING":
                continue
            note, spec = page["review"], page["review_source"]
            stored = identity._checked_source(spec, lambda s: api.file(s["path"], s["ref"]))
            prior = api.get("git/commits/" + spec["ref"])
            now = current(value["pdf_sha256"], page["page_number"])
            once.require(stored == once.raw(note) and prior["sha"] == spec["ref"]
                and pages.read.clock(note["reviewed_at"]) <= pages.read.clock(prior["committer"]["date"])
                <= pages.read.clock(clock()) and now is not None and now[0] == note,
                "FULL_QUESTION_TRUSTED_REVIEW_CHANGED")
