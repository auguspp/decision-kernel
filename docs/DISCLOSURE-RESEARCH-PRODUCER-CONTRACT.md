# Disclosure Research Producer Contract v0

This is the external semantic-Research handoff for one official company-disclosure batch.

It is intentionally small. The producer interprets evidence and returns existing Research Method v1 objects. It does **not** invent a disclosure-specific route, terminal state, Human wake decision, Recommendation, or investment authority.

## Runtime flow

```text
CNINFO reality
  -> frozen-Research freshness
  -> exact quiet-receipt suppression
  -> official PDF / Evidence qualification
  -> DisclosureAssessmentPacket
  -> external semantic Research producer
  -> DisclosureResearchAssessment
  -> existing Research Funnel
       -> WAIT_FOR_TRIGGER -> quiet receipt
       -> DROP_FOR_NOW     -> quiet receipt
       -> DEEPEN_REQUIRED  -> actionable, no receipt
  -> Human Surface is not invoked by this disclosure-assessment path
```

The packet is the producer's immutable input. The assessment is the producer's semantic output. `run_disclosure_research_assessment()` validates the exact handoff and delegates routing to the existing `run_research_funnel()`.

## Producer output shape

Return one JSON object accepted by `DisclosureResearchAssessment`:

```json
{
  "assessment_input_hash": "<exact packet assessment_input_hash>",
  "discovery": { "...": "DiscoveryInput" },
  "pre_research": { "...": "PreResearchResult" },
  "quick_research": null,
  "supplemental_evidence_artifacts": [],
  "schema_version": 1
}
```

Do not hand-maintain a duplicate JSON schema. Generate the current machine-readable schema directly from the installed model:

```bash
python - <<'PY'
import json
from decision_kernel.runtime.disclosure_research import DisclosureResearchAssessment

print(json.dumps(
    DisclosureResearchAssessment.model_json_schema(),
    ensure_ascii=False,
    indent=2,
    sort_keys=True,
))
PY
```

This contract is Research Method v1 policy. The model is the source of truth for field-level validation.

## Exact bindings that must be preserved

The producer must carry forward the packet identity rather than reconstructing a similar-looking case:

- `assessment_input_hash` must equal the packet's exact `assessment_input_hash`.
- `discovery.source_lane` must equal the packet source lane (`CNINFO`).
- `discovery.ticker` must equal the packet stock code.
- `discovery.as_of` must equal the packet `prepared_at` PIT cutoff.
- `discovery.source_lineage` must preserve the **entire exact official Evidence batch** from the packet. Do not omit one announcement and do not replace official packet Evidence with supplemental Evidence.
- Discovery observations may interpret the official batch, but every referenced evidence id must exist in declared lineage.
- `pre_research.discovery_id` and `pre_research.as_of` must preserve the exact Discovery identity and PIT cutoff.
- FACT / MARKET_CONTEXT claims must carry Evidence lineage as required by the existing Research Funnel models.
- If Pre Research returns `CONTINUE_TO_QUICK`, a valid `quick_research` is required. If Pre Research returns `WAIT_FOR_TRIGGER` or `STOP`, do not supply Quick Research.
- Quick Research must reference the exact Pre Research state through `pre_research_hash` and preserve the same Discovery identity / PIT cutoff.
- Supplemental Evidence is allowed for bounded Research enrichment, but ids must be unique, must not overlap the packet Evidence ids, and must have been available by the packet PIT cutoff.

The consumer fails closed if these identities or clocks are changed.

## What the producer must not output

Do **not** add or infer any of the following fields or authorities:

- `terminal_state`
- `assessment_disposition`
- `receipt` / `seen`
- `human_attention` / `attention_eligible`
- `recommendation`
- `position_size`
- `trade_action`
- `investment_authority`

The producer may choose the existing Pre / Quick Research routes because those are Research Method v1 outputs. It may not declare the final Funnel terminal state independently. The existing Funnel derives `WAIT_FOR_TRIGGER`, `DROP_FOR_NOW`, or `DEEPEN_REQUIRED` from the validated Research objects.

Investment authority remains `NONE`.

## Quiet memory semantics

A receipt does **not** mean "this announcement has been seen."

It means the exact official announcement batch has completed the current assessment semantics against the exact frozen Research identity. Current cheap suppression therefore keys on:

```text
stock_code
+ exact announcement_ids
+ research_snapshot_id
+ research_as_of
+ assessment_semantics_id
```

`assessment_input_hash` is intentionally used to bind the semantic assessment at apply time, not as the cheap future-scan lookup key. Requiring packet hashes during scan suppression would force PDF acquisition before the noise filter could do its job.

Only validated quiet Funnel outcomes create receipt memory. `DEEPEN_REQUIRED` stays actionable and unreceipted.

## Operational handoff

The scheduled `decision-inbox` workflow publishes an `official-disclosure-scan` artifact containing any still-unassessed packet files under `disclosure-assessment-packets/`.

For the GitHub manual path, run `apply-disclosure-assessment` with:

1. the exact `decision-inbox` scan run id;
2. the exact packet filename shown in the scan summary;
3. compact `DisclosureResearchAssessment` JSON produced from that packet.

The workflow downloads the packet from that exact prior run, restores best-effort receipt memory, runs the production consumer, saves new memory only when a quiet receipt is actually recorded, and publishes an audit snapshot of packet + assessment + Funnel result.

For local/manual validation of the same boundary:

```bash
decision-kernel apply-disclosure-assessment \
  packet.json \
  assessment.json \
  --receipts decision-state/disclosure-receipts.json
```

A valid quiet result is success. A valid `DEEPEN_REQUIRED` result is also success, but it writes no receipt and does not automatically invoke Human Surface.

## Current proven dogfood outcome

The CATL 2026-08-27 disclosure loop has been exercised against the real CNINFO filing:

```text
7 research-uncovered
-> 6 prior quiet receipts suppressed
-> 1 exact assessment packet
-> existing Pre Research = WAIT_FOR_TRIGGER
-> 1 new quiet receipt
-> next real scan: 7 seen-suppressed / 0 unassessed
-> 0 Human Surface calls
```

That is the intended success shape: new reality enters, objective and contextual noise disappears, and only research context that genuinely needs more cognitive budget remains actionable.
