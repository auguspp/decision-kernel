# Disclosure cognition regression corpus

This directory is Harness-owned evaluation state, not Kernel constitution.

Its purpose is to answer one narrow question before changing an LLM, prompt, or semantic Research producer:

> Given the same frozen Research context and the same official disclosure Evidence, did the replacement cognition method become better, worse, or merely different?

The corpus deliberately starts with naturally encountered CATL official-disclosure cases. It is not a synthetic benchmark and it is not a second Radar.

## State class

These fixtures live in Git because they are durable epistemic evaluation truth: frozen inputs plus reviewed baseline judgments that should remain inspectable across model and prompt changes.

They are different from:

- disclosure receipts, which remain lossy Actions-cache attention optimization;
- Actions artifacts/logs, which remain short-lived operational trace;
- credentials, which remain Secrets;
- production ResearchSnapshots, which remain the actual versioned investment Research state.

A corpus case never becomes a receipt merely because a candidate model agrees with the gold result.

## Frozen input

Each case points to one serialized `DisclosureAssessmentPacket` under `packets/`.

The packet already binds:

- exact `ResearchSnapshot` id, as-of, and information-bundle hash;
- exact CNINFO announcement set;
- assessment semantics id;
- official EvidenceArtifact identity;
- PDF SHA256 and extracted-text SHA256;
- page-by-page extracted text;
- one deterministic `assessment_input_hash`.

The v0 CATL packets were rebuilt through the production packet seam with `prepared_at = 2026-09-02T07:00:00Z`. Before freezing, every official PDF SHA256 was asserted against the hash observed in the earlier natural-runtime investigation.

The legal-opinion filing in the 2026-08-12 batch is intentionally retained even though extraction yielded no text. A model must not invent evidence just because another filing in the same dated batch is material.

## Gold output

`catl-v0.json` stores reviewed semantic expectations, not a second executable Research router. For each case it records:

- expected `DROP_FOR_NOW` or `WAIT_FOR_TRIGGER` terminal result;
- expected terminal stage (`PRE_RESEARCH` or `QUICK_RESEARCH`);
- factual gold claims and the announcement ids that support them;
- the largest unresolved question;
- the next discriminating evidence;
- a short reason for the stop/wait decision.

The baseline comes from closed experiment PR #44, which routed these exact six historical batches through the existing Research Method v1 funnel against the frozen CATL Research context.

These labels are evaluation gold for this corpus version. They do not create investment authority and they do not make Research Method v1 part of Kernel law.

## Candidate-run provenance

A candidate run is a small JSON manifest. It names the corpus and records producer-level provenance plus one assessment file per case:

```json
{
  "schema_version": 1,
  "run_id": "gpt-x-prompt-v2-2026-09-02",
  "corpus_id": "cninfo-catl-disclosure-cognition-v0",
  "producer": {
    "provider": "example-provider",
    "model": "example-model",
    "producer_version": "research-producer-v2",
    "prompt_version": "disclosure-prompt-v2"
  },
  "cases": [
    {
      "case_id": "300750-2026-07-30",
      "assessment_path": "outputs/300750-2026-07-30.json",
      "raw_response_path": "raw/300750-2026-07-30.txt",
      "invoked_at": "2026-09-02T08:00:00Z"
    }
  ]
}
```

`raw_response_path` may equal `assessment_path` when the provider already returns strict structured JSON. The scorer hashes both raw response bytes and parsed assessment state; model/provider identity, prompt/producer version, and invocation time remain operational provenance only.

Run the deterministic scorer from the repository root:

```bash
python eval/disclosure_cognition/score_candidate_run.py candidate-run.json \
  --output candidate-score.json
```

A complete, structurally valid run exits `0` even when its semantic routes drift from the reviewed gold. Missing cases, unexpected cases, malformed output, or exact packet/PIT/Evidence binding failures exit non-zero because the run is not auditable. This avoids silently turning the gold labels into Kernel authority.

## What v0 scores automatically

The deterministic scorer measures only things the system can know without inventing another semantic judge:

1. **Input binding failures** — changed assessment input, ticker, PIT cutoff, source lane, or official Evidence lineage fail through the existing production validator.
2. **Evidence-reference integrity** — referenced Evidence must exist in the exact packet or explicitly supplied supplemental Evidence. V0 does not pretend that an existing citation semantically entails a prose claim.
3. **Route drift** — DROP / WAIT / DEEPEN differences versus the reviewed baseline.
4. **Stage drift** — Pre versus Quick differences, including stage inflation.
5. **DEEPEN overcall** — candidate DEEPEN decisions where the reviewed case remained quiet.
6. **Structural unknown / next-evidence presence** — counts are reported for audit, but prose quality is not scored by string heuristics.

The scorer records a terminal confusion table plus per-case raw-response SHA256, assessment JSON SHA256, parsed assessment canonical hash, routes, terminal state/stage, supplemental Evidence count, and investment authority. It never writes a disclosure receipt and never invokes the Human surface.

## What still requires semantic review

These questions remain deliberately outside deterministic v0 scoring:

- whether a prose claim is actually entailed by the cited page text;
- whether an unknown is economically important rather than generic;
- whether proposed next Evidence would genuinely discriminate the frozen thesis;
- whether a route drift is an improvement, a regression, or a defensible alternative interpretation.

A future Human or model-judge layer can evaluate those questions against the same frozen packets, but that judge is itself replaceable evaluation policy, not Kernel law.

The corpus should grow only from real cases encountered in dogfood or operation. Do not manufacture breadth just to make the benchmark look larger.
