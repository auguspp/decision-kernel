# Decision Kernel

Decision Kernel is the small, explicit investment-decision core extracted from Decision OS.

It is **not** Decision OS v2 and it is **not** a new platform build.

## Operating principles

1. **Own only investment cognition semantics.** Evidence/PIT, research state, belief, market observation, odds, rehearsal, authority, lineage, and Human-surface eligibility belong here when they are genuinely Decision-Kernel-specific.
2. **Reuse commodity infrastructure.** Market-data transport, news aggregation, HTTP, retries, scheduling, process supervision, logging, storage plumbing, and UI stay outside the core and should use mature tools/services with thin boundaries.
3. **Modular monolith, thin workflow.** Modules stay independently understandable; a small application workflow connects them. No plugin platform, event bus, provider framework, or orchestration framework by default.
4. **Quiet stop is a product outcome.** A workflow may deepen, wait, drop, stop quietly, or wake the Human. It does not need to run every stage.
5. **Human authority stays final.** Research, Odds, and Decision Rehearsal never become an autonomous investment decision, position size, portfolio action, execution instruction, or capital authority.
6. **Extract proven core; do not wholesale-copy the old repository.** Existing Decision OS implementations and tests are source material. Transitional plumbing stays behind unless it proves it belongs in the kernel.
7. **Reuse-first gate for new code.** Before adding non-unique infrastructure, check mature prior art first. A thin adapter is preferred to an owned subsystem.

## Current shape

```text
external sensing
      |
      v
Discovery -> Pre Research -> Quick Research
      |             |
      |             +-> WAIT / DROP
      v
DEEPEN_REQUIRED
      |
external Deep Research capability
      |
      v
DeepResearchPackage
      |
readiness + commit gate
      |
      v
ResearchSnapshot + HiThink ObservedMarket
      |
      v
Odds -> Decision Rehearsal -> Human Surface
                              |
                         quiet / wake Human
```

Authority and lineage constrain the whole chain. HiThink transport is an outer runtime concern; `adapters/hithink.py` only qualifies provider payloads and translates them into `ObservedMarket`.

## Minimal live command

The first executable seam intentionally starts from an already-produced `DeepResearchPackage` JSON. It does not yet execute upstream Deep Research itself.

```powershell
python -m pip install -e .
$env:HITHINK_FINANCE_API_KEY = "<your key>"
decision-kernel run .\path\to\deep-research-package.json
```

The command fetches only the HiThink trading calendar and raw daily history needed for the security, requires the raw history to reach the latest completed A-share session, applies the preserved `decision-os-live-odds-v0.1` policy, and prints a compact Human-facing result.

A normal quiet result is valid. `INSUFFICIENT_ODDS` does not wake the Human. Only `HumanResearchSurface.status + attention_eligible` controls Human attention. Investment authority remains `NONE`.

## Boundaries

```text
runtime/hithink_http.py
    HTTP + API key + request construction
             |
             v
adapters/hithink.py
    provider payload qualification
             |
             v
ObservedMarket
             |
             v
Decision Kernel core/workflow
```

Do not add by default:

- dashboard framework
- provider registry/framework
- fallback market provider
- retry/backoff framework
- scheduler framework
- process supervisor
- generic artifact service
- agent framework
- portfolio construction or sizing
- trade execution

The success condition is not feature parity with Decision OS. The success condition is a smaller, harder investment-decision core that is easier to run, replace around, and trust.
