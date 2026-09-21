# Research output diagnostics: preserve the contract and reject unchanged

Scope: #297/5757262828, following the actual failed Woton call35569495879 and
its separate review in #486. This change is diagnostics, not a new invocation,
model-output repair, provider reliability certification or economic acceptance.

## What changes

The original `saved_research_once.model_call` now writes the post-adapter
`text.format` to `<stage>-output-format.json` using create-only local I/O before
contacting the provider. The existing Actions artifact carries it alongside the
input, output and usage. `output_format_sha256` remains the hash of these same
bytes; `output_format_file` is assigned only after the write succeeds. This is
the prepared SDK output format, not a historical packet capture. A local file
conflict stops before sending, with `phase=REQUEST_RETENTION`; it never overwrites.

On a Pydantic application rejection the original usage additionally records
`application_validation`: total errors, at most20 field-location/type entries,
and an explicit omitted count. Only declared Pre/Quick/ResearchClaim field names,
bounded indices and a finite error-type vocabulary are copied. Arbitrary field
names and custom error codes are redacted. Input, message, context, URLs and
exception strings are not included. Native Pydantic still rejects the unchanged
output; a diagnostic failure cannot replace the original exception. Transport,
output-retention and application failures remain distinct.

No SYSTEM, model/SDK parameter, generated schema, admitted Evidence allowlist,
Pre/Quick validation, prompt budget, authority, request policy, retry or workflow
change. The consumed Woton intent, its raw output, r3 and original failures remain
unchanged. No paid call, source acquisition, market request or new daily slot.

## Reuse and evidence

Reuse Decision: REUSE / THIN_ADAPTER in the existing call, no new dependency.
Internal sources at432d92e: original model_call, raw-retention/SSE tests,
Pre/Quick models, the retained Woton response and CI mainline protocol.

Official/native contracts inspected:
- DeepSeek Responses `text.format` documents json_schema with type/name/schema:
  https://api-docs.deepseek.com/api/create-response/
- Pydantic native errors API supports excluding input/context/URL; the helper
  deliberately also ignores messages and filters locations/types:
  https://docs.pydantic.dev/latest/api/pydantic_core/#pydantic_core.ValidationError.errors
- The actual OpenAI SDK v3.11.0 converter adds strict while retaining schema:
  https://github.com/openai/openai-python/blob/v3.11.0/src/openai/lib/_parsing/_responses.py
  (Git blobbinding c607587ec18a65ed4e6e263d1e73eea6f8d6703a).

Mature public prior art: the existing SDK and HTTPX MockTransport implementation
https://github.com/encode/httpx/blob/0.28.1/httpx/_transports/mock.py
were inspected. Tests use the SDK's already installed `httpx2` transport seam,
as the repository's existing raw-retention tests do; no transport dependency is
added or replaced. Pydantic remains the sole application validator; there is no
second JSON-schema engine, output fixer, retry library, agent or parser framework.
Existing licenses/dependency boundaries remain; no speculative replacement build.

## What the tests establish, and what they do not

The real raw Woton output stays invalid at material_claims[15/16/17].kind.
An unmodified original SDK constructs HTTP JSON into an in-process mock transport.
Tests compare that whole request with the original request builder, verify all
four claim kinds and exact admitted IDs, and compare the Woton output-schema,
format and SYSTEM hashes with the actual retained usage. This distinguishes a
missing/altered client contract from a response that violates the supplied
contract. It does not establish server internals or guarantee future compliance.

The already accepted DeepSeek strict-field compatibility fix is preserved;
adding strict back, flattening schema references, lowering temperature or
repairing UNKNOWN into another kind is not justified by this sample. The system
text's use of UNKNOWN could be ambiguous, but that remains a hypothesis, not
proven causation or permission to rewrite a frozen request. Unknowns belong in
the original unknown fields, not a fifth ResearchClaimKind.

Local21 diagnostic/adapter-seam tests are run on retained source plus the exact
current saved_research_once blob and unchanged native Pre dependencies; the
container cannot clone GitHub by DNS and lacks the pinned SDK. The real-SDK HTTP
regressions require full hosted CI, with no skip or local fallback. An initial
local test expected two errors but native Pydantic also reported the invalid
required tuple; the new test expectation was corrected, not the validator.
Full exact-head CI, independent main CI, normal publication and fixed-ref readback
remain separately recorded release gates. No future result is preclaimed here.
