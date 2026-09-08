# P0-3 accepted; P0-4A execution validation in progress

This is a thin engineering/acceptance index, not a new daily result, Research record,
Human decision, pending-request registration, or production recovery source.

## P0-3 demand-side acceptance received

The Human-supplied notice titled "验收交接及施工通知：P0-3 消费验收通过 → P0-4A 单案例 Pre／Quick 真实执行闭环"
explicitly accepts saved-result consumption at:

- repository: `auguspp/decision-kernel`
- reading ref: `read-model/current-state`
- accepted reading commit: `e7ad9591a3139b568708a8d927494027d45da924`
- entry: `current-state.json`, instructions: `README.md`
- corresponding code commit: `ae34998136d4546f7470e3877212c16f202419d8`
- supplied notice SHA256: `c51c4f58bba22c845e15ba342d61ab0c338dc9dc0c6a7a916a02f01c9bd8b30b`

ENGINEERING/CI and REMOTE READ ENTRY remain established by #282/#283.
SAVED-RESULT CONSUMER ACCEPTANCE = PASS for that exact reading package, by the demand side.
This does not assert that all underlying lanes were healthy, or sign a later reading package.
P0-3 producer-event refresh, P0-1 natural schedule acceptance, and P0-2 natural page
publication remain independently pending; fully unattended recovery is not established.
The README table formatting and Stock CHECK_INCOMPLETE-detail improvements remain separate
non-blocking P0-3 follow-ups; they are not included in this P0-4A change.

## P0-4A engineering and isolated candidate

- #284 merged code: `30a28c0763d56b74d82c06ac544b724fe265f41d`.
- #284 PR CI: `34222990075`, test job `102050266069`, 2069 passed in 511.69s.
- #284 main CI: `34223916077`, test job `102053296610`, 2069 passed in 639.09s.
- Existing domain models and original `run_research_funnel()` are unchanged.
- #285 is the isolated candidate DRAFT; do not merge or register it as accepted Research.
- Original candidate commit: `8848943b91a36d41534c6aff8cdb70e1d8d3632d`.
- Candidate directory: `research_runs/candidates/605296.SH/p0-4a-605296-2026-09-08-v1/`.
- Files: `input.json`, `candidate.json`, `funnel.json`.
- Frozen research cutoff: `2026-09-08T12:17:30Z`; market observation is 2026-09-07.
- Recorded proposed route: Pre CONTINUE_TO_QUICK -> Quick WAIT_FOR_TRIGGER.

The candidate receipt reports 9 tool events, 5 queries, and 4 successful source reads.
That last count consists of two GitHub input/test reads and two external business sources;
it is not four externally read company/industry documents. A receipt's platform-reference
strings and self-reported model label do not alone authenticate execution history or model
version. Do not silently promote them into platform attestation.

## Remaining acceptance boundaries

The added base-only-install test exercises a real clean virtual environment, installs only
the existing base package, and runs schema generation plus a synthetic original-Funnel
validation outside the checkout. It does not perform Research or certify the real candidate.
Its success is established only by the CI that actually executes it, not by this document.

Keep these separately evidenced:

1. engineering/full CI and actual minimal-runtime execution;
2. real Pre and Quick execution with retained source/receipt provenance;
3. original-Funnel deterministic validation of the exact candidate;
4. remote candidate/result readback;
5. demand-side semantic acceptance;
6. the bounded normal/adversarial real-executor comparison.

Reading one attack fixture during an execution is not an independently isolated matched
normal/adversarial experiment. Likewise a source-derived instruction whitelist is a soft
boundary unless the actual runtime restricts tools and writes. No unattended research
writeback or broad model-safety certification is established here.

Historical April operating data and a July H1 earnings forecast can test an unqualified
bullish explanation; without later operating/cash data they do not establish September
fundamentals or causally explain the September price observation. Preserve that limitation
when reviewing the original candidate, rather than treating JSON/CI validity as semantic
acceptance. Subsequent source re-checks must retain their own clocks and must not overwrite
the original receipt, cutoff, failed reads, or candidate bytes.

Continue on #285 for candidate readback and semantic disposition; record engineering
installation evidence separately. Do not reimplement #284 or resume the resolved Tinavi
handoff. #263 remains an independent draft.

No new market acquisition, schedule, provider budget, retry, Deep/Odds, registry write,
Human wake, or investment authority. The 18:13 Sector schedule and original fail-closed
restore/publication boundaries remain unchanged.
