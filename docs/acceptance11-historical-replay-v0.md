# #321 Acceptance 11 — Historical Research replay input v0

Status: **BOUNDED REPLAYABILITY CONTRACT / REUSE / NO NEW EXECUTOR**  
Scope: #321 Acceptance 11 only. Investment Authority = `NONE`.

## 1. Acceptance question

The original requirement is that a retained Hengrui case be sufficient for:

```text
same Evidence
same Research cutoff
new model / prompt
→ historical replay
```

and therefore must not consist only of final prose.

This requirement is about **future replay input identity**, not a promise that a second model will reproduce the original judgment, and not permission to silently fetch newer evidence. A new replay result is a new candidate Research result. It does not overwrite the historical result, inherit Human acceptance, or gain Investment Authority.

## 2. Reuse decision

Reuse Decision: **REUSE**.

No replay engine is added. Existing objects already provide the required identities:

- `EvidenceArtifact` owns source identity, PIT availability, content hash, retention mode and replayability qualification;
- `ResearchSnapshot` / `ResearchCommitPackage` own the frozen Evidence links and cutoff;
- Direct Deep #415 retained the exact root request, source captures, EvidenceArtifacts, pass trace, Research package and generic commit result;
- Git/GitHub archive and fixed commits already own immutable file identity.

The only missing human-readable seam is an **output-independent replay-input manifest** that tells a future model/prompt exactly which inputs may be consumed and which prior outputs must stay hidden until comparison.

## 3. Replay packet

`docs/readings/600276-hengrui-direct-deep-dogfood-2026-09-17/replay-input.json` binds:

- company/security identity;
- `research_cutoff = 2026-09-17T09:57:00Z`;
- original Research request identity;
- the Full Research v3 method identity;
- the exact four retained EvidenceArtifact ids/content hashes and source-capture pointers;
- a new replay prompt contract;
- the exact prior outputs excluded from replay input.

The future replay prompt must use **only** that retained Evidence set and cutoff. It may change model/prompt and therefore interpretation, UNKNOWN disposition or candidate thesis, but it may not change source set, PIT cutoff or source qualification and still call the run “same Evidence / same cutoff”.

Prior outputs are comparison material only after the new candidate is frozen. In particular the replay input excludes the old `core_thesis`, pass summaries, `commit-result.json` and README findings. This prevents “replay” from degenerating into paraphrasing the saved answer.

## 4. Replayability is qualified, not binary

The fresh #415 Hengrui Evidence set intentionally contains four `EXTRACTED_VALUES / PARTIAL` EvidenceArtifacts. Existing `EvidenceArtifact` validation explicitly forbids `EXTRACTED_VALUES` from claiming `FULL` replayability.

Therefore two claims must remain separate:

```text
EXACT RETAINED EVIDENCE-SET REPLAY INPUT = ESTABLISHED
FULL ORIGINAL WEB/PDF SOURCE REPLAY = NOT ESTABLISHED FOR THIS CASE
```

A future model can receive exactly the same retained structured observations, source qualifications, limitations, source locators and cutoff. It cannot claim to have re-read every original page/PDF byte unless those bytes were separately retained as `FULL_ARTIFACT / FULL` evidence.

This is not a defect to repair by indiscriminately copying licensed or transient source content. Source retention should follow the original permission/retention contract.

## 5. Regression acceptance

The acceptance tests require:

1. replay cutoff exactly equals the #415 request cutoff and ResearchSnapshot cutoff;
2. replay Evidence ids/content hashes exactly equal the committed fresh package Evidence set;
3. every EvidenceArtifact was available by the frozen cutoff;
4. each replay evidence pointer resolves to the retained `source-captures.json` entry whose canonical hash is the EvidenceArtifact content hash;
5. all four artifacts remain `EXTRACTED_VALUES / PARTIAL`; no FULL claim is invented;
6. replay prompt and input manifest do not contain the old thesis or rely on `pass-records.json`, `commit-result.json` or README findings;
7. changing the future `model_or_prompt_version` leaves the Evidence+cutoff identity unchanged.

This proves that the historical case supports a new-model/new-prompt replay **from the retained Evidence set**. It does not claim a new model has already produced an independent result, nor that an alternate result would be more correct.

## 6. Acceptance interpretation

If the full suite passes, record Acceptance 11 as:

`PASS_WITH_SCOPE — SAME_RETAINED_EVIDENCE + SAME_CUTOFF REPLAY INPUT ESTABLISHED; FULL-SOURCE REPLAY PARTIAL`.

No model/provider framework, source downloader, scheduler, persistence layer, Market/Odds path, Action or Investment Authority is added.
