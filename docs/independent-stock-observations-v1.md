# Independent Stock observations from retained full-market pages

This is a bounded original C2 / P2-4 consumer, not completion of C2 or independent
live acquisition. It reads existing decoded provider envelopes offline, preserves
the complete source denominator and freezes a small sample before checking which
stock histories happen to be available. No Sector trigger, membership, company
link or previous Research admits a candidate.

Authority remains the [original P2-4 scope](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5835074681)
and [C completeness correction](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5909499946).
AI Investment Authority = NONE. No production workflow, live Stock current-state admission,
dispatch, schedule, source request, provider, dependency, Research or Watch change.
A passive `NAVIGATION_ONLY / ON_DEMAND_ARCHIVE` locator for the derived report may
use the existing archive index. It does not admit a live Stock reading, eagerly
materialize a source, or claim custody of the original large archive.

## Reuse decision: REUSE + THIN_ADAPTER

- Internal: `sector_radar_audit.validate_sector_radar_input_audit_integrity` binds
  the original inventory; the existing full-market parser owns pagination,
  duplicate/total/null/zero/clock checks. The recorded calendar, benchmark snapshot
  and benchmark history qualify a comparison session without reading a Sector
  result. `hithink_stock_reading.qualify` retains 26 required recent own-stock bars,
  61-calendar-session context, exact request identity, receipt clocks, price,
  volume/turnover and corporate-action checks
- Arithmetic: `stock_radar_reading._stock_path` remains a backward-compatible
  state-facing wrapper around its unchanged sessions-only body. No `_observe`
  policy, v7/v8/v9 selection, issuer isolation or serialization rule changes
- Official: [HiThink prices contract at 3bca7805](https://github.com/HiThink-Tech/Financial-API/blob/3bca7805a4127ece8d81961917e740d2effac6ec/docs/api/a-share/prices.md)
  documents full-code-table pages and provider-ready timestamps. A page does not
  provide a per-security trading date or Chinese company name
- External: the retained #508/#511 review and current EasyStock
  `37a8c1bb3e2e9cabeb11f94dbef50a8b955f1948` `radar.go`, tests and license were
  inspected for this increment. Its theme/industry assembly, fallback and strength
  semantics do not solve independent exact-source replay. No code copied or
  dependency adopted; the PolyForm Noncommercial restriction remains relevant to
  any future adoption

The source audit's producing implementation hashes are retained separately from
the consuming implementation hashes. Loading its integrity is deliberately not
ordinary producer replay: the original exact-implementation replay validator is
unchanged and still requires the original code bytes.

## Consumer and output contract

Run `python -m decision_kernel.runtime.independent_stock_observations` with:

```text
--audit-root <retained>/market-context/input-audit
--audit-hash <independently recorded audit_hash>
[--stock-root <retained>/reading --capture-hash <independently recorded capture_hash>]
--sample-size 16
--output <new sibling directory>
```

Use `PYTHONPATH=src` for an uninstalled source checkout. `--verify <directory>`
replaces `--output` to rebuild the JSON from the separately pinned inputs and
verify the exact two-file inventory and rendered README bytes. A pin copied from
an untrusted modified report is not an independent source identity.

Every consumed context, session, page and stock-trace file is read once at its
point of use; those exact bytes must match the length and SHA-256 in the already
pinned audit/capture inventory before they are parsed. An earlier whole-tree
validation does not authorize a later unchecked reread. If a source changes
between inventory validation and consumption, the consumer fails without
publishing a result. Parsing uses the checked buffer, not another filesystem read.

The output pair is `observations.json` and `README.txt`, published through the
existing atomic, create-only report helper. Failed source qualification publishes
no successful empty result. Output cannot be inside an input tree. No network or
saved source script is executed; an absent/unplanned request never falls back to
a provider. Stock response-bearing receipts require exact integer HTTP 200. The
older Sector audit records decoded JSON and `error_type`, not HTTP status; no
missing transport evidence is invented.

The deterministic result does not record a new analysis clock. Its source capture
and receipt clocks remain historical; none is relabeled as the later replay time.

The all-market sample origin is `INDEPENDENT_ALL_MARKET_SNAPSHOT`. The rule is
descending absolute `(last_price / prev_price) - 1`, then exact code, K from 1 to
16, computed using the existing Decimal convention at precision 28. This is an
unvalidated replay display/sample rule. It is not Surprise, investment rank,
economic novelty, liquidity/tradability certification or a production gate. Large
positive and negative moves are retained; unknown name-based risk classification
is not treated as a pass.

The compact derived inventory has explicit columns and one row for every source
identity, ordered by code. Each row joins a page descriptor carrying exact file
SHA-256, bytes, original request parameters and capture clock, then a zero-based
position in that page's original `data.item`. The row retains last/previous price,
the signed difference numerator and an explicit selected/deferred/unpriced
disposition. The ratio denominator is the same previous price. The page hash and
position bind the whole original row, including omitted fields; no standalone
row-hash archive or reconstructed original-envelope claim is made.

Selection is frozen and hashed before reading the history capture. Missing
selected histories remain `UNKNOWN / HISTORY_NOT_SUPPLIED`; available traces
cannot replace them. The complete denominator, selected count, supplied-history
intersection and successfully qualified intersection are separate. Older own-bar
gaps can null 60-day context while a missing recent required bar fails; no gap is
filled and no corporate action is automatically adjusted.

The separate replay-control panel retains the original historically Sector-selected
traces. It is not an independent discovery panel, even if a control also happens
to lie in the independently frozen sample. Provider code 3002 remains a request
failure, never an empty corporate-action history. Per-security session proof,
company name, business benefit and economic interpretation stay UNKNOWN or
NOT_ESTABLISHED where the source does not supply them.

## Real retained replay: 2026-09-30

Source: [run 36702153468](https://github.com/auguspp/decision-kernel/actions/runs/36702153468),
artifact `11091190335`, `stock-reading-36702153468-1`, produced at
`ce22fa79ac841dea11d31541c86e4c4faeb1378b`.

- ZIP SHA-256: `47f4ea4d31f4d575ebb5d16c64269aaaafc280d6ed5e07dc4cce35e6c333fec8`
- Audit hash: `81a3eaeb66b18bf03679756c3d4cdacf339b6b05f7e2e9ba61e8069cba8958f7`
- Stock capture hash: `2aa308ce96a5d020141b086f0b0d26379610bf85dc9afe1b3569d8d09477f446`
- Source pages: `market-context/input-audit/responses/0015.json`–`0026.json`
- Source custody expiry: **2026-12-29T10:23:49Z**. The original archive and combined
  12-page set exceed the 512 KiB report bound. They remain external Actions-retained inputs;
  this lossy derived inventory is not their permanent custody, a compressed copy,
  or a split-file workaround. Hashes cannot recover expired missing bytes

The original Sector audit binds 42 files and the Stock capture binds 43 files.
Their request/response bytes are checked before consumption. The original
`reading/stock-reading.json` is used only as a separate regression comparator,
never as this consumer's input substitute.

Actual result:

- 5,578 unique identities across 12 complete pages; 5,560 usable last/previous
  quote ratios and 18 unpriced identities
- K=16 frozen independently; 5,544 priced rows deferred, all still represented
- Two selected identities have supplied history: `920344.BJ` qualifies;
  `688806.SH` preserves the corporate-action request failure, provider code 3002
- Fourteen selected identities remain `HISTORY_NOT_SUPPLIED`. The single qualified
  intersection is a retained historically selected trace, not evidence of a newly
  discovered, successfully investigated company
- Separate controls: `600072.SH`, `600802.SH`, `300904.SZ`, `920344.BJ` reproduce
  qualified raw paths exactly; `688806.SH` preserves code 3002; `600585.SH`
  preserves `PRICE_REFERENCE_DISCONTINUITY_REQUIRES_SEPARATE_REVIEW`

A separate comparison using the existing `build_stock_discovery_pool` on the
original retained result yields 45 Sector-leader identities, pool hash
`4cc85312306211085fbcbaa0b6b862ca8d556dde96f79e3adf334fde5f0152c4`.
The complete snapshot includes 5,533 identities outside that pool, 5,515 priced.
Eleven of the 16 sampled identities are outside that pool. These are coverage
differences, not counts of valuable discoveries. The comparator is not an input
gate in the independent consumer.

The [retained derived report](readings/c2-independent-stock-observations-2026-09-30/observations.json)
keeps the exact selected identities, source joins, qualifications and failures.
Its [generated summary](readings/c2-independent-stock-observations-2026-09-30/README.txt)
is part of the verified pair. Retention does not claim remote publication,
independent later consumption, Human acceptance or full C2 acceptance.

## Verification and remaining gates

Focused synthetic tests prohibit network and cover absent Sector/Research data,
signed deterministic ordering, the complete denominator, history-independent
selection, null/coherent-zero preservation, missing/extra/truncated/duplicate
pages, inconsistent totals/offsets, future clocks, original request/session pins,
HTTP receipt contradictions, 26-required/61-context behavior, rehashed origin and
source tampering, unchanged inputs and atomic create-only pair verification.
Legacy Stock tests separately exercise the unchanged wrapper and old consumers.

This archive was acquired on an active Sector day. Synthetic no-Sector tests prove
consumer independence, **not quiet-day live acquisition**. New independently
sampled histories, Surprise policy/value, false-positive and lead-time evidence,
attention cost, natural consumption and the original remaining P2-1–6 scope stay
open. No new live acquisition or Research permission is inferred from this replay.
