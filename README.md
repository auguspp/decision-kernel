# Decision Kernel

Decision Kernel is the small, explicit investment-decision core extracted from Decision OS.

It is **not** Decision OS v2 and it is **not** a new platform build.

## Operating principles

1. **Own only investment cognition semantics.** Evidence/PIT, research state, belief, market observation, odds, rehearsal, authority, lineage, and Human-surface eligibility belong here when they are genuinely Decision-Kernel-specific.
2. **Reuse commodity infrastructure.** Market-data transport, news aggregation, HTTP, retries, scheduling, process supervision, logging, storage plumbing, and UI should use mature external libraries/services with thin adapters.
3. **Modular monolith, thin workflow.** Modules stay independently understandable; a small application workflow connects them. No plugin platform, event bus, provider framework, or orchestration framework by default.
4. **Quiet stop is a product outcome.** A workflow may deepen, wait, drop, stop quietly, or wake the Human. It does not need to run every stage.
5. **Human authority stays final.** Research, Odds, and Decision Rehearsal never become an autonomous investment decision, position size, portfolio action, execution instruction, or capital authority.
6. **Extract proven core; do not wholesale-copy the old repository.** Existing Decision OS implementations and tests are source material. Transitional plumbing stays behind unless it proves it belongs in the kernel.
7. **Reuse-first gate for new code.** Before adding non-unique infrastructure, check mature prior art first. A thin adapter is preferred to an owned subsystem.

## Intended shape

```text
commodity sensing / HiThink
          |
          v
   thin adapters
          |
          v
Evidence / PIT
     |
Attention
     |
Research
     |
Belief + Observed Market
     |
Odds
     |
Decision Rehearsal
     |
Human Surface
     |
quiet / wake Human

Authority + Lineage constrain the whole chain.
```

## Initial extraction order

The repository starts deliberately small.

1. Decision spine: Evidence primitive → ResearchSnapshot → ObservedMarket → Odds → Rehearsal → Human Surface.
2. Research funnel semantics.
3. Attention/Radar semantics without sensing-provider plumbing.
4. Proven HiThink market-data access as a thin adapter.
5. External sensing via reuse-first adapters.
6. Thin natural workflow.
7. Commodity UI and scheduling only after the core workflow is proven.

## Explicit non-goals

Do not add by default:

- dashboard framework
- provider registry/framework
- retry/backoff framework
- scheduler framework
- process supervisor
- generic artifact service
- agent framework
- portfolio construction or sizing
- trade execution

The success condition is not feature parity with Decision OS. The success condition is a smaller, harder investment-decision core that is easier to run, replace around, and trust.
