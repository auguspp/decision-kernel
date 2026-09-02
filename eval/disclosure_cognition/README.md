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

A future LLM runner should record operational provenance alongside each candidate output:

- model/provider identifier;
- prompt or producer version;
- invocation time;
- exact packet `assessment_input_hash`;
- raw response SHA256;
- parsed `DisclosureResearchAssessment` SHA256 or canonical hash;
- parser/validation errors, if any.

That provenance is for audit and comparison. It must not automatically enter Kernel constitution or disclosure-receipt identity.

## What to score

The first useful regression metrics are deliberately semantic rather than agentic:

1. **Input binding failures** — changed ticker, PIT cutoff, source lane, packet hash, or official Evidence lineage.
2. **Unsupported claims** — claims that cannot be traced to Evidence in the frozen packet or explicitly supplied supplemental Evidence.
3. **Route drift** — DROP / WAIT / DEEPEN differences versus the reviewed baseline.
4. **Stage inflation** — especially a tendency to turn routine disclosures into Quick/Deep Research without discriminating evidence.
5. **Unknown quality** — whether unresolved questions remain decision-relevant rather than generic.
6. **Next-evidence quality** — whether the producer asks for evidence that could actually discriminate the frozen thesis.

The corpus should grow only from real cases encountered in dogfood or operation. Do not manufacture breadth just to make the benchmark look larger.
