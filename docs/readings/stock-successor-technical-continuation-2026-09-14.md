# Stock successor technical continuation — 2026-09-14

This note records a bounded runtime repair after the first production Stock
successor attempt. It is not company Research, semantic acceptance, investment
judgment or a new Human authorization.

## Canonical failed execution

Production workflow run `34797952444` was dispatched once on main
`23670560b79bb4b21f5f32fb60959b4044dd2910` with:

- `source-stock-run-id=34673882756`;
- `source-successor=true`;
- `recover-sources=false`;
- `prepare-sources=false`.

Both authorized companies created their fixed `source-successor-v1/` children
and then stopped during `SOURCE_PREPARATION` with `AttributeError` before formal
Research. No SDK Pre preview/request, provider Pre, validator/Funnel or Quick was
reached. The resulting Stock work commit is
`f53fdd6c0f1bb6088a8eae9a1363d35a975dbbb9`; the normal fixed reading exposing
that failure is `eb17ca1694057fe24dad51c99c9cec9aaf431ff6`.

The exact failed workflow artifact is `10330128020`,
`stock-business-research-34797952444-1`, 15,816,299 bytes, SHA256
`9b9bab464bceee731e3090fe799a4defffacf7208bd9fa8e17034a3750ef4b9c`.
It retains the two child reservations/failures/host receipts, batch receipt,
source-successor binding, original Stock archive and the previously verified
source-only ZIP.

## Established defect

`stock_source_successor.capture()` imported runtime `cninfo_http` as `cninfo`
and evaluated `cninfo.SHANGHAI_TZ` before any CNINFO inventory request. The
runtime HTTP seam does not export that timezone object. The existing original
Stock source implementation imports `SHANGHAI_TZ` from `adapters.cninfo`.

The repair therefore reuses that existing timezone contract directly. It does
not change the CNINFO provider, query scope, PDF transport, parser, page-reading
logic, source clocks, model or request-byte limits.

## Legal continuation identity

The failed `source-successor-v1/` children are create-only canonical history and
must never be reopened. A fixed sibling
`source-successor-continuation-v1/` is the only technical continuation for:

- `603353.SH` Heshun Petroleum;
- `300711.SZ` Guangha Communications.

The frozen continuation request binds the exact failed run/artifact, failed work
commit, failed fixed reading, each predecessor successor `prepare.json` and
`failure.json`, Human permission #297 comment `5652950925`, the already-consumed
source-recovery predecessors and the exact saved source-only material.

A changed price, date, permission number, code version or representation hash
cannot create another continuation identity. Existing files under the fixed
continuation prefix block another attempt through the original create-only
Retainer.

## Original executor remains authoritative

The continuation only selects/binds a new child identity and supplies the same
saved-source capture adapter. The executor remains the original
`stock_research_host.run_item()` followed by the original admission,
full-input storage/decode, exact SDK pre-send check, Pre, conditional Quick,
validator and Funnel.

Quick may occur only after a validated real Pre route requests it. A source,
identity, permission, provider or technical failure remains a gap and must not
be represented as WAIT. There is no automatic retry, Deep, Odds, Action, trade,
position or monitoring authority.

The original fixed reader preserves the failed `source_successor` history and
reads any technical continuation separately under the same root company item.
A continuation candidate is not Human semantic acceptance or a registered
investment handoff.

## Acceptance boundary

Code acceptance requires fixed-head PR CI/review, independent main CI and
ordinary fixed-reading publication/readback before any production continuation
dispatch. The code CI is not proof that CNINFO is unchanged, that Sub2API accepts
the real request, or that either company reaches a particular Funnel state.
