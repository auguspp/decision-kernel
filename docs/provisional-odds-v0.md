# Human price / same-Research Odds adapter v0

Engineering scope: #321-B, bounded contract in issue comment 5696470475.
This is a pure Python consumer API, not a new valuation engine, provider, live CLI,
workflow, automatic archive, watch registration, or production adoption receipt.

## What it does

`decision_kernel.provisional_odds` accepts a previously validated **COMMITTED**
ResearchSnapshot and a separately typed `HumanPriceContext`. It binds the exact
snapshot id, information-bundle hash and full canonical snapshot hash. It does
not execute Research, call a provider, mutate either input or perform I/O.

A Human context must explicitly declare ticker, exchange, currency, positive
Decimal-compatible price, timezone-aware price timestamp and supplied-at time,
exchange-local UTC offset, price convention, and the reference to the actual
Human price statement. Timestamps and labels are declarations, not verified facts.
The source remains `HUMAN_SUPPLIED_PROVISIONAL_PRICE / CONTEXT_ONLY`, with both
market-qualification flags false. Do not invent a Human statement to run a sample.

When frozen Research already declares supported numerical worlds, the adapter
passes those exact inputs to existing `calculation.calculate_valuation_odds()`.
The old arithmetic input field name `observed_market_price` denotes a number in
that pure arithmetic API; **no ObservedMarket object is constructed**. Scenario
probabilities already in Research are neither changed nor defaulted. Although the
existing engine computes its aggregate internally, the provisional projection
omits every scenario probability, weighted aggregate and participation-zone
field. It does not establish cardinal probabilities or their calibration.

The provisional output preserves individual dated distributions, per-share
payoffs and undiscounted cumulative returns. Its `ordinal_status` is **only the
sign pattern over those declared worlds**: all positive, all negative, all break
even, or a mixed/zero-containing set. This is not a complete downside assessment,
a likelihood ordering, a favorable/unfavorable investment judgment, a required-
return test, an annualized return, or a buy recommendation. Positive nominal
returns alone say nothing about whether compensation for time and risk is adequate.

A valid schema-v2 Research-only snapshot without numerical worlds/horizon produces
an explicit `PROVISIONAL / NO_CALCULATION / ORDINAL_NOT_ESTABLISHED` result. It does
not get zero returns, invented probabilities or a fabricated valuation horizon.
This v0 does **not** parse narrative/Markdown worlds into numerical ones. Invalid
supplied numerical state is rejected rather than discarded to obtain success.
FX conversion, total-equity distributions, passed expected distributions and an
expired frozen horizon remain unsupported. There is no implicit FX, split/
adjustment conversion, dividend removal or rolling of the valuation date.

## Reuse and caller responsibilities

Before use, recover and revalidate Research through the existing #321-A
commit/archive contract (`research-commit-only-v0.md`, `research-archive-v0.md`).
A shape-valid ResearchSnapshot by itself cannot prove an exact Evidence set or
source authenticity. The caller must also check the case's current qualification,
method-review notices and Research eligibility. Old CATL/CMB qualification exits
are not repaired by this module. A matching hash does not prove that there is no
new external Evidence or thesis challenge; affected Research must be explicitly
revised/re-underwritten rather than silently reused.

`recompute_canonical_odds()` takes **another**, independently source-qualified
ObservedMarket, explicit market ticker/exchange, and the existing Odds policy.
It verifies the prior provisional calculation against the **same full frozen
Research**, then calls the original `odds.build_odds_research()` unchanged. It
never converts or copies the Human context into an ObservedMarket. Differences
in Research, convention, currency, security or exchange-local offset are rejected;
comparison cannot reverse result or price chronology. The original horizon,
world definitions, dated cash flows and declared probabilities remain unchanged.

**ObservedMarket currently carries no ticker or provider-qualification receipt.**
Its caller must use the existing provider qualification path and bind the actual
security before invoking this adapter. The separate ticker/exchange arguments,
type check and rejection of an explicitly Human-labelled market source are not
an authenticity certificate. Do not manually build an ObservedMarket from a
Human price or treat an arbitrary deserialized market object as qualified. This
module neither fetches/qualifies market data nor solves historical source gaps.

The comparison retains both distinct artifacts and the signed price difference.
`PRICE_ONLY_SAME_FROZEN_RESEARCH` describes a same-Research recomputation, **not**
an in-place authority upgrade of the prior artifact. Canonical policy/context
are explicit inputs of the canonical side; the provisional sign pattern has no
policy zone to compare. Do not attribute different semantic labels to price
alone. Legacy canonical probabilities remain declared frozen inputs, not newly
calibrated probabilities, Human acceptance or investment authority.

## Consumer example

The paths below are caller-owned inputs, not supplied company examples or a new
CLI. This only saves a local create-only result; it does not register/publish it.

```python
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from decision_kernel.runtime.research_commit_only import read_retained_commit
from decision_kernel.provisional_odds import (
    HumanPriceContext, FrozenProvisionalOdds,
    build_provisional_odds, verify_provisional_odds,
)

# First recover the exact eligible archive using the existing archive contract.
snapshot = read_retained_commit(Path("recovered-research")).research_snapshot
context = HumanPriceContext.model_validate_json(Path("human-price.json").read_bytes())
result = build_provisional_odds(
    research_snapshot=snapshot, price_context=context,
    artifact_id=uuid4(), created_at=datetime.now(timezone.utc),
)
with Path("provisional-result.json").open("xb") as output:
    output.write((result.model_dump_json(indent=2) + "\n").encode("utf-8"))
loaded = FrozenProvisionalOdds.model_validate_json(Path("provisional-result.json").read_bytes())
verify_provisional_odds(loaded, snapshot)
```

For a separately qualified observation supplied by the caller's existing market
path, call `recompute_canonical_odds(provisional=loaded,
research_snapshot=snapshot, observed_market=qualified_observation,
market_ticker=actual_ticker, market_exchange=actual_exchange,
artifact_id=uuid4(), created_at=now, policy=existing_policy)`.
Read a serialized comparison as `SameResearchOddsComparison`, then use
`verify_same_research_comparison(comparison, snapshot)` to rebuild **both** sides.
Parsing and a checksum are not deterministic-computation verification. The
verifiers reject rehashed numerical/probability edits; they do not authenticate
an invented source or replace the independently pinned archive identity.

Market/consumer failure leaves the already retained Research and provisional
artifact intact. No function calls `live.py`, generates a Human request, accepts
Research/Odds on the Human's behalf, creates an Action, or enables a watch.

## Acceptance boundary

Regression tests use synthetic fixtures only. They cover original-engine
arithmetic parity, numerical absence, source/type separation, unsupported cash
flows, clocks/conventions, full-Research identity changes, rehashed edits, wire
round-trips and no optional provider/model imports or network use. Legacy
canonical and Funnel tests remain unchanged and blocking.

A green CI proves that code contract, not real-company provisional→canonical
acceptance, current Research truth, natural production, automatic cross-chat
publication, or any investment judgment. Existing manual/ordinal company
artifacts are not automatically migrated or made numerical by this v0. #321-B's
real eligible case, durable result integration and production consumption remain
separate bounded acceptance work; the wider #321 is not closed by this module.
