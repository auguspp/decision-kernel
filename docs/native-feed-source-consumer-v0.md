# Native feed source scanning and exact completion receipts — v0

Status: OFFLINE CONNECTOR / COMPLETE SOURCE-SCAN RECEIPTS / NOT MARKET DELIVERY OR NATURAL NEW-SOURCE PROOF.

This slice connects the existing native feed exporter to the existing literal theme-source scanner. It deliberately leaves `radar_feed_intake`, `EvidenceArtifact`, source publication-time policy and market computation unchanged. It uses the same original-feed verifier, source discovery, parser, canonical identity and static HTML renderer. No queue, database, crawler, library, workflow, source fetch, authority or Kernel object is added.

## Distinct states, not a generic acknowledgment flag

1. Seen in RSS: the existing append-only registry owns versions and first-observed clocks. Initial baseline entries are not candidates.
2. Source scan completed: a verified receipt proves that the listed exact qualified descriptions went through the existing matcher under one catalog/method/industry-probe scope. A plan or a completed no-literal-match result can qualify; a blocked scan cannot.
3. Market acquisition: a source-scan receipt does **not** prove that its plan ran, succeeded, was published, entered Research or reached Human. `PLAN_NOT_EXECUTED` remains explicit. Historical plans stay visible when the next source scan has nothing new; they cannot silently be reactivated with stale market state.

All outputs continue to declare `source_delivery_acknowledged=false`, `article_accepted=false` and `human_review_recorded=false` where applicable. The source registry is never rewritten, pruned or used to trigger market transitions. The word receipt here means deterministic source-scan completion, not general delivery acknowledgment.

## How to run

Install the existing optional `feeds` environment. Supply a fully retained successful feed capture, an exact saved Sector state, and a JSON context containing only `concept_catalog`, `industry_catalog`, and `industries`, using the existing capture-record formats. The explicit receipt directory must exist, even when empty. It contains only complete previously generated successful scan bundles and an optional empty `.gitkeep`; a missing directory or loose receipt JSON is not an empty successful history.

```sh
mkdir -p /work/registered-source-scans
python -m decision_kernel.runtime.radar_feed_consumer scan \
  --feed-capture /work/source-run/capture \
  --market-state /work/saved-market-state.json \
  --context /work/exact-catalog-context.json \
  --receipts-dir /work/registered-source-scans \
  --as-of 2026-09-06T08:00:00+00:00 \
  --output /work/source-scan-attempt

python -m decision_kernel.runtime.radar_feed_consumer verify \
  --output /work/source-scan-attempt
```

The example time is an explicit cutoff, not a promise that these paths or a qualifying current state exist. CLI generation time is the actual current clock; replay uses saved original times. Existing stale-state/catalog guards remain active. The normal producer must not bridge a missing market session to serve this consumer.

Only after successful verification should an operator explicitly copy the **whole** completed scan bundle into the registered directory. Output cannot be inside that store or any source capture, and an existing output is never overwritten. There is no automatic registration/latest lookup, implicit initialization, remote restore, schedule, market request or ingestion of a Human source review. A failed/quiet attempt has no completion receipt and must not be registered as one.

## Exact selection and reuse

Each run first reconstructs the original feed capture and applies the unchanged **whole-export** time/text/capacity guard. It validates current supplied catalogs/state with the existing scanner, then verifies registered receipts by rebuilding their original source scans. Only receipts matching the source observation initialization, provenance, exact original source identity/clocks, matcher version, concept catalog, industry catalog and explicit industry probes suppress repeated scanning. Receipt copies deduplicate; no record count is an independent-source or forecast count.

A changed concept catalog or probe scope requires a new scan; old plans remain labeled historical. A new feed representation has a different content identity and is not suppressed. An already-seen version keeps its original first-received/recorded time. A future receipt cannot remove an earlier pending source. One unqualified new date or description remains a whole-batch blocker; previously completed scans do not make the bad source disappear. No timezone is inferred and RSS titles are not promoted to article body evidence.

**Deliberate remaining capacity boundary:** this adapter does not decrease the existing intake's `pending_versions` or its full 32-source export bound. Even previously scanned versions still count in that upstream contract. A 33-version export fails closed before suppression. A long-lived consumer therefore still needs an explicitly reviewed bounded delivery/batching protocol; this PR does not claim an indefinitely advancing feed-to-market service. There is no silent first-N choice or disguised budget increase.

## Bundle and verification scope

A successful bundle contains the complete copied `feed-capture/`, exact `context.json`, serialized `market-state.json`, `selection.json`, rebuilt `source-discovery.json`, existing `index.html`, `scan-receipt.json`, a per-attempt `handoff.json`, and `files.json`. Refusals and quiet attempts retain their original source and diagnostics but contain no scan receipt. Publication uses a temporary directory and final rename, with a single writer and no partial completed output on failure.

Verification reconstructs each listed source from original feed bytes, enforces its strict export qualification, repeats the existing matcher/planner, and compares the exact report, receipt and HTML. Rehashing fake output is insufficient. The source initialization/capture and all first clocks remain independently visible. The market state is a read-only comparison input, not a new state recovery authority.

Historical receipt bundles remain separate. `handoff.json` references which prior receipt hashes were supplied; a standalone receipt proves its **listed** completed source scans, not that the operator supplied every historical receipt or that an external history was never lost. Full selection-history reproduction requires those prior bundles. A deliberately empty existing store is an explicit scope, not a claim of global exactly-once processing. Hashes are not authentication or permanent storage. Complete remote publication, archive lifecycle and executed-market acknowledgments remain separate work.

The archive guard is 32 MiB / 32 files per scan bundle and 64 registered receipt directories. Exceeding it requires explicit archive/capacity review rather than pruning or truncating. No original PDF, entire article body, additional feed response or prior full ancestor chain is manufactured.

## Evidence limits and acceptance

Tests run real feedparser, capture/succession/rebuild, source export and theme discovery using synthetic transport only. They check exact receipt reuse, new-version-only scanning, no-match versus blocked scans, denial context, changed catalog scope, persistent unexecuted plans, unqualified/future dates, 33-source refusal, changed bytes and rehashed false execution, receipt chronology, missing/loose/foreign stores, atomic writes, and full CLI verification. Source and market inputs are unchanged.

The latest real RSS successor remains run **34012474393**. Its 1000 records are unchanged baseline content, with unzoned publication strings and zero post-baseline candidates. This slice performs no re-fetch and produces no natural new-source, qualified-publication or live source-to-market evidence. Earlier real proofs remain historical. Human / Research / Investment / signal-transition authority stays NONE; no third canonical wake or company judgment is created.
