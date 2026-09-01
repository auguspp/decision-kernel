# Decision Kernel

Decision Kernel is the small, explicit investment-decision core extracted from Decision OS.

It is **not** Decision OS v2 and it is **not** a new platform build.

## Operating principles

1. **Own only investment cognition invariants.** PIT, exact lineage, frozen state identity, deterministic Odds inputs, Human accountability, authority boundaries, and Human-surface eligibility belong here when changing them would break the decision system itself.
2. **Research method is versioned policy, not constitution.** A useful research recipe can be strict without becoming a permanent Kernel invariant. `research_contract_v1.py` preserves the current Decision OS method separately from kernel acceptance.
3. **Reuse commodity infrastructure.** Market-data transport, news aggregation, HTTP, retries, scheduling, process supervision, logging, storage plumbing, and UI stay outside the core and should use mature tools/services with thin boundaries.
4. **Modular monolith, thin workflow.** Modules stay independently understandable; a small application workflow connects them. No plugin platform, event bus, provider framework, or orchestration framework by default.
5. **Quiet stop is a product outcome.** A workflow may deepen, wait, drop, stop quietly, or wake the Human. It does not need to run every stage.
6. **Human authority stays final.** Research, Odds, and Decision Rehearsal never become an autonomous investment decision, position size, portfolio action, execution instruction, or capital authority.
7. **Extract proven core; do not wholesale-copy the old repository.** Existing Decision OS implementations and tests are source material. Transitional plumbing stays behind unless it proves it belongs in the kernel.
8. **Reuse-first gate for new code.** Before adding non-unique infrastructure, check mature prior art first. A thin adapter is preferred to an owned subsystem.

## Constitution vs Research Contract

Use one hard test before adding or requiring a Research field:

> If this field disappears, does PIT, Belief, Odds, exact lineage, or Human accountability become invalid?

If yes, it may belong to the Kernel. If no, it belongs to a versioned research method or presentation layer until proven otherwise.

Examples:

**Kernel invariants**

- evidence cannot leak from the future
- frozen Research identity and hashes cannot silently change
- a Scenario distribution used by Odds must be complete and probabilities must sum to one
- Odds must use the exact committed ResearchSnapshot and exact market observation
- belief / market expectation / invalidation required by the Human decision surface remain explicit
- investment authority remains `NONE`

**Decision OS Research Contract v1 policy**

- require FACT + INFERENCE + ASSUMPTION claim classes
- require variant perception and richer research narratives
- require fundamental / expectation / liquidity clock assessments
- require three to five monitoring indicators
- use a two-to-five-scenario research set
- require explicit scenario assumptions and financial drivers
- require bounded adversarial review

Those v1 rules can remain excellent research discipline without becoming permanent Kernel law.

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
Research Contract v1 (method policy, when selected)
      |
      v
DeepResearchPackage
      |
kernel acceptance + commit
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
