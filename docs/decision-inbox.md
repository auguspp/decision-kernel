# Decision / Attention Inbox v0.3

The Inbox is the Human-facing shell over **existing** Research and Decision outputs. It is deliberately ticker-centric at the front and drill-down oriented behind each card.

It does **not** create a new score, Research route, Decision wake gate, recommendation, or investment authority.

## Two existing input lanes

The front door may compose two already-authoritative kinds of output:

```text
Research Funnel
→ DEEPEN_REQUIRED
→ Research attention card

Decision Spine
→ HumanResearchSurface.attention_eligible == true
→ Decision-review card
```

These semantics remain different.

`DEEPEN_REQUIRED` allocates **Research budget**. It means the existing Research Method v1 has found enough decision-relevant uncertainty to justify deeper underwriting. It is not a canonical Decision wake and it is not a buy signal.

`HumanResearchSurface.attention_eligible == true` remains the sole canonical **Decision wake** owned by the Decision Spine.

The Inbox only projects those existing outputs into one Human surface.

## Ticker-centric front, complex background

The intended Human loop is:

```text
open latest Attention Inbox
        |
        +--> nothing worth attention -> close it
        |
        +--> one or a few tickers -> read:
              - why it is worth looking at
              - current Research / Odds state
              - discovery source / Research disposition
        |
        +--> only then drill down into evidence, unknowns, Belief and monitoring
```

For a cold-start company with `DEEPEN_REQUIRED` but no frozen Research, the surface must say so explicitly:

```text
尚未建立 frozen Research
Odds 未生成
```

It must not manufacture a Belief, probability, valuation, Odds state, Human Decision, or Action merely to make the card look complete.

When a new discovery maps to an already-researched ticker, the surface may join the existing Decision Spine output by ticker so the Human can see the current Research / Odds state next to the new Research question. The new discovery does not silently mutate the frozen Research.

## Research attention handoff

`decision_kernel.runtime.attention_inbox` accepts either:

1. a serialized existing `ResearchFunnelResult`; or
2. a thin Harness wrapper:

```json
{
  "company_name": "英维克",
  "research_funnel": { "...": "validated ResearchFunnelResult" }
}
```

`company_name` is presentation metadata only. The wrapper is not a `KernelModel`, has no schema version, and adds no state-machine or authority semantics. PIT lineage and the Research route remain owned by the embedded `ResearchFunnelResult`.

Only `DEEPEN_REQUIRED` handoffs appear on the front surface. `WAIT_FOR_TRIGGER` and `DROP_FOR_NOW` remain collapsed as background Research dispositions.

## Scheduled production composition

The GitHub Actions workflow `decision-inbox` runs automatically on A-share weekdays after the market close. It now invokes the same ticker-centric composition root used for Research attention replay:

```bash
python -m decision_kernel.runtime.attention_inbox
```

The workflow owns two separate, explicit Harness lists:

```text
decision_packages
research_attention_handoffs
```

`decision_packages` contains the currently curated Research packages that may be run through the existing HiThink live path.

`research_attention_handoffs` may contain only exact, unresolved, validated `ResearchFunnelResult` handoffs that currently retain `DEEPEN_REQUIRED`. It must not become a wildcard, directory scan, or file-presence rule.

The current scheduled Research-attention list is intentionally empty. The accepted Tinavi cold-start handoff remains valuable frozen dogfood, but Full Research has already been completed and the Human state is now WATCH / NO_ACTION. Replaying that old handoff every weekday would incorrectly recreate a stale cold-start `DEEPEN_REQUIRED` card.

Operating rule:

```text
new unresolved DEEPEN_REQUIRED handoff
→ explicitly add its exact path to the scheduled list

Full Research / Human disposition resolves the attention request
→ remove the path from the scheduled list
→ retain the frozen handoff as audit lineage
```

A checked-in package or handoff may remain useful as a historical mechanics fixture, shadow-observation input, disclosure-acquisition anchor, or audit artifact after current Human-facing eligibility has ended. File presence alone must never restore eligibility.

The legacy Decision-only command remains available:

```bash
decision-kernel build-inbox dogfood/300750-catl.json research_cases/002050-sanhua-deep-research-v1.json
```

The ticker-centric Research-attention composition can be replayed with:

```bash
python -m decision_kernel.runtime.attention_inbox \
  dogfood/300750-catl.json \
  research_cases/002050-sanhua-deep-research-v1.json \
  --research-attention path/to/research-attention-handoff.json
```

Both surfaces write:

- `decision-inbox/index.html` — dependency-free, mobile-friendly static snapshot
- `decision-inbox/summary.md` — the same Human surface for GitHub Actions Job Summary

## Boundary

The Inbox is presentation/runtime Harness. It may:

- render already-derived Research Funnel and Human Surface outputs;
- group multiple `DEEPEN_REQUIRED` questions for the same ticker into one ticker card;
- join an already-researched ticker to its current Research / Odds display state;
- collapse background Research dispositions and quiet researched cases.

It must not:

- decide a Research route itself;
- turn `WAIT_FOR_TRIGGER` into `DEEPEN_REQUIRED`;
- retain a resolved handoff as recurring current attention;
- change Fundamental Belief from price/path evidence;
- alter Odds thresholds;
- create a second canonical Decision wake;
- infer a Human Decision or Action;
- create investment authority;
- persist a new canonical case state merely for presentation.

Research attention and Decision review can share one front door without becoming the same authority.
