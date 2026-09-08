# Xiamen Tungsten Decision Hygiene Negative Control — Research Error, Not Human Decision Error

Status: **FROZEN DOGFOOD / HISTORICAL RESEARCH-PROCESS NEGATIVE CONTROL / NO CONSTITUTION CHANGE**  
Security: **厦门钨业 / Xiamen Tungsten / 600549.SH**  
Historical source PIT: **Decision OS case retrospective recorded 2026-08-22**  
Method note: `docs/decision-hygiene-method-note-2026-09-03.md`  
Recorded: **2026-09-03**

## Purpose

After three live Decision Hygiene dogfoods — YTO, GigaDevice and Sanhua — the working Constitution-review threshold required a negative control:

> Can the new methodological distinctions improve attribution on a historical case where the investment process was materially wrong, rather than merely making current research sound more sophisticated?

The historical Decision OS repository does **not** currently contain a clean case that satisfies the strongest version of that requirement:

```text
frozen Human investment judgment
+ later realized outcome
+ sufficient PIT lineage
+ honest adjudication that the Human judgment was materially wrong
```

The closest useful case is Xiamen Tungsten because its own contemporaneous retrospective explicitly documents material research mistakes and corrections before any Human Decision or Action was frozen.

Therefore this artifact is deliberately narrower:

> **It is a research-process negative control, not a Human-decision negative control.**

It tests whether Decision Hygiene can classify genuine, already-documented research failures without hindsight or outcome contamination.

It does **not**:

- claim that the Human made a wrong investment decision;
- use later share-price performance to label the case a miss;
- invent an Outcome that the historical record does not contain;
- change Kernel Constitution;
- add schema, enums, state machines, or failure-attribution objects;
- create a new ResearchSnapshot or Odds state;
- issue a Recommendation, Human Decision, Action, or investment authority.

The original Decision OS retrospective remains immutable prior art.

---

## 1. Negative-control verdict first

```text
NEGATIVE CONTROL TYPE = RESEARCH-PROCESS ERROR
HUMAN DECISION ERROR CONTROL = NOT AVAILABLE IN REPOSITORY
HISTORICAL HUMAN DECISION = NONE / NOT YET FROZEN
HISTORICAL ACTION = NONE
HISTORICAL OUTCOME = NONE

REFERENCE FRAME / MODEL-CLASS FAILURE = MATERIAL
INFERENCE FAILURE = MATERIAL
ASSUMPTION / DRIVER-OMISSION FAILURE = MATERIAL
PROBABILITY FAILURE / THEATER = MATERIAL
VALUATION / TIMING FAILURE = MATERIAL
EVIDENCE FAILURE = NOT THE PRIMARY PROBLEM
CLASSIFICATION FAILURE = NOT THE PRIMARY PROBLEM
ODDS FAILURE = NOT ADJUDICABLE
EXOGENOUS SURPRISE = NOT NEEDED AS EXPLANATION

DECISION HYGIENE ATTRIBUTION VALUE = YES
PROBABILITY QUALIFICATION AT THE CORRECTED PIT = NOT ESTABLISHED
RESEARCH STOP / WAIT STATE = LEGITIMATE
CONSTITUTION CHANGE = NOT AUTHORIZED BY THIS CONTROL
```

The main result is:

> **Decision Hygiene does improve failure attribution on a known research mistake: the case was not mainly “bad data” or “bad luck.” It was an incorrectly framed causal model that then contaminated inference, probability and valuation.**

That is a stronger learning signal than simply saying the research became more cautious.

---

## 2. Historical record — preserve what the old case actually said

The frozen Decision OS retrospective explicitly states that the early research path became persuasive before it became decision-ready.

The early story was approximately:

```text
H1 attributable profit ~CNY2.2bn
+ ~CNY1.1bn inventory impairment looks unusually high
→ normalized earnings may be CNY4.4–4.7bn
→ if impairment does not repeat, earnings may approach CNY5.0bn
→ share price around CNY55 may therefore offer some odds
```

The retrospective then records that this apparently coherent bridge was incomplete because the dominant upstream variable — **tungsten price regime** — had not been made explicit.

It further records that:

- H1 earnings occurred in an unusually high tungsten-price environment;
- those earnings could not be annualized while simultaneously assuming a materially lower long-run tungsten-price regime;
- scenario probabilities such as `25/50/25`, later `20/45/35`, were assigned before the driver model was complete;
- Dahutang and other future-project economics initially received too much mature-state treatment before ownership, capex, quotas, timing and attributable economics were properly decomposed;
- future mature earnings were too easily translated into present valuation without adequate time / probability / capital treatment;
- the integrated tungsten business was initially treated too linearly as `tungsten price ↑ → earnings ↑` despite multiple upstream/downstream transmission channels;
- after correction, the original excitement around CNY55 became harder to justify;
- Human Decision, Action and Outcome remained unfrozen / pending.

This is unusually valuable negative-control material because the errors were documented **inside the research process itself**, not reconstructed after a later stock outcome.

---

## 3. What was not wrong: Evidence was not the main failure

The retrospective did not discover that the important historical source records were fabricated or unavailable.

The research had real observations:

- H1 reported earnings;
- inventory impairment;
- tungsten resource quantities;
- project ownership / rights information;
- mine / project descriptions;
- market price context.

The dominant failure was not:

```text
source said X
but X was copied incorrectly
```

Nor was it primarily:

```text
secondary source was promoted into primary realized FACT
```

The more important failure was:

> **Correct or plausible observations were assembled under an incomplete Reference Frame and then translated into economic conclusions too quickly.**

This distinction validates the Decision Hygiene note's separation between Evidence / Classification failures and downstream model / inference failures.

---

## 4. Reference Frame Failure — the highest-level error

### Early implicit frame

The early analysis behaved too much like:

> **asset-rich industrial company with temporarily depressed accounting earnings and valuable future resources**

Under that frame, the most salient facts became:

- H1 profit;
- impairment normalization;
- large tungsten resources;
- future mine/project profit potential.

The frame encouraged a bridge from attractive assets to normalized profit without first asking what commodity regime generated the current earnings.

### Corrected frame

The retrospective moved toward a more appropriate model class:

> **integrated cyclical tungsten business whose earnings curve depends on commodity price, upstream self-sufficiency, downstream pass-through, inventory effects, ownership, project timing, capex and changing internal resource mix.**

Under this frame, the first-order causal chain becomes:

```text
long-run tungsten price / cycle state
→ input and realized selling-price transmission across segments
→ upstream vs purchased-feed economics
→ inventory / working-capital effects
→ segment margins
→ contribution from existing operations
→ new resource self-sufficiency
→ project capex / quota / timing / ownership
→ attributable cash earnings
→ through-cycle ROIC / owner FCF
```

The change is not cosmetic.

It changes which historical periods are comparable, what earnings can be normalized, what base rates matter, what future projects mean, and how valuation should be translated through time.

### Failure attribution

```text
REFERENCE FRAME FAILURE = MATERIAL
```

Why this matters:

> Many later mistakes were not independent mistakes. They were downstream symptoms of the wrong model class.

This is exactly the type of error that a generic `assumption wrong` label would hide.

---

## 5. Inference Failure — incompatible economic regimes were silently combined

The early normalization logic effectively combined:

```text
current high-tungsten-price H1 earnings
+ assumption that impairment may not recur
+ lower / more normal long-run commodity-price intuition
```

without rebuilding the operating economics under one coherent commodity-price regime.

That produced a persuasive but internally inconsistent inference.

A normalized earnings number is not valid merely because each component sounds individually reasonable.

The correct discipline is:

> **All material earnings inputs in one Research World must belong to the same causally coherent state of the world.**

For Xiamen Tungsten:

```text
high H1 earnings under high tungsten price
```

cannot silently coexist with:

```text
lower long-run tungsten-price assumption
```

while preserving the same segment-profit run rate.

### Failure attribution

```text
INFERENCE FAILURE = MATERIAL
```

This is a clean example of why Scenario must mean a **joint causal world**, not independently favorable marginal assumptions.

---

## 6. Probability Failure / Probability Theater — weights appeared before the driver model

The old retrospective explicitly records probability sequences such as:

```text
25 / 50 / 25
then
20 / 45 / 35
```

before the causal model had made tungsten price explicit.

That is almost a textbook instance of the architecture concern now exposed by the live dogfoods:

```text
Research needs terminal scenarios
→ terminal scenarios need probabilities
→ probabilities must sum to one
→ producer supplies a numerically complete distribution
→ numerical completeness creates an illusion of epistemic maturity
```

The underlying problem was not that `25%` should have been `20%`.

It was that the research had not yet established the objects to which probability should attach.

A more mature ordering would have been:

```text
Reference Frame
→ tungsten-price states / supply-demand regimes
→ resource-self-sufficiency states
→ project timing / ownership states
→ transmission into segment earnings and cash
→ dependency between those states
→ only then ask whether probability can be established
```

At the corrected historical PIT, the case itself concluded that the favorable structural-earnings outcome had **not** been proven strongly enough to be the base case.

### Failure attribution

```text
PROBABILITY FAILURE / PROBABILITY THEATER = MATERIAL
```

The key learning is not “never assign probabilities to cyclicals.”

It is:

> **Probability should not be demanded before the Reference Frame and causal driver states are decision-ready.**

---

## 7. Valuation Failure — future mature economics were pulled too close to the present

The retrospective also documents a separate but related valuation mistake.

A future earnings state such as:

```text
CNY4.5bn after Bobai / Dahutang / other projects mature
```

was too easily treated as if it supported the 2026 share price through a simple earnings multiple.

But a mature future state requires explicit treatment of:

- years until realization;
- probability / path to realization;
- capex before realization;
- ownership leakage;
- quotas and permitting;
- operating ramp;
- interim commodity cycles;
- dilution or financing where relevant;
- required return for waiting.

Therefore:

```text
future mature earnings
× terminal multiple
```

is not automatically present fair value.

### Failure attribution

```text
VALUATION / TIMING FAILURE = MATERIAL
```

This category remains distinct from Probability Failure:

- even a correctly identified future world can be valued incorrectly today;
- even a correct valuation translation cannot rescue an unqualified probability measure.

---

## 8. Assumption Failure vs Uncertainty Hygiene

The old research also compressed several project-level uncertainties too quickly into successful mature-state economics.

For Bobai / Jiujiang / Dahutang, material unresolved items included:

- license / permit status;
- mining / production quota;
- construction or restart schedule;
- capex;
- ownership economics;
- operating cost;
- production ramp;
- cash realization timing.

These uncertainties did not all share the same origin.

Conceptually:

| Variable | Uncertainty origin | Resolution path |
| --- | --- | --- |
| long-run tungsten price | Future-state + structural | supply/demand, project pipeline, inventory, policy, realized prices |
| mine quota / permit | Future-state / regulatory | official approval / quota evidence |
| project timing | Future-state | construction / restart milestones |
| capex | Estimation + future-state | company disclosure / realized investment |
| ownership economics | Measurement / legal-economic mapping | ownership structure, agreements, cash attribution |
| mine operating cost | Estimation + measurement | production disclosures / realized cost data |
| resource self-sufficiency benefit | Model / structural | same-price segment economics as internal-resource share rises |

The old method tended to compress these into a mature earnings number.

Decision Hygiene instead asks:

> **Which uncertainties can be reduced by more diligence now, which require future observation, and which should remain modeled rather than researched away?**

That would likely have stopped the research from converting unknown future-project states into apparent present precision.

---

## 9. Retrospective Fit — why the corrected frame is genuinely better

A reinterpretation should not be accepted merely because it sounds more sophisticated.

The corrected integrated-cyclical frame explains historical observations that the early frame struggled with:

1. **High H1 earnings and attractive asset value can coexist with weak current Odds** if the earnings are generated by an unusually favorable commodity regime.
2. **A large resource base does not mechanically equal listed-company value** because ownership, quota, capex and time mediate the transmission.
3. **The same tungsten price can produce different future listed-company earnings** if resource self-sufficiency changes the internal cost curve.
4. **Higher tungsten price is not one fixed earnings slope** because upstream, smelting, powder, carbide, tools and wire can experience different pass-through and inventory effects.
5. **A mature future profit number does not imply current cheapness** when realization is distant and capital intensive.

Therefore:

```text
RETROSPECTIVE FIT = STRONGER UNDER CORRECTED FRAME
```

The new explanation earns the right to replace the old one because it resolves prior contradictions, not because a later stock outcome favors it.

---

## 10. Prospective Discrimination — how the new frame exposes itself to being wrong

The corrected thesis compressed to an explicit forward question:

> **If long-run tungsten prices return to a more normal mid-range regime, can higher resource self-sufficiency and future projects make Xiamen Tungsten structurally more profitable than it previously was at the same commodity price?**

This creates a proper prospective test.

### If the structural self-sufficiency thesis is right

At comparable tungsten-price regimes over time, Research should eventually observe:

```text
higher internal-resource share
→ structurally better attributable segment economics
→ improved through-cycle margin / cash conversion
→ adequate incremental ROIC after capex
```

### If it is wrong

Even after new resource capacity matures:

```text
same commodity-price regime
→ no meaningful through-cycle earnings uplift
or
→ uplift is consumed by capex / ownership leakage / poor utilization
→ owner economics do not improve sufficiently
```

This is a better falsifiable proposition than:

> “Dahutang is a large resource, therefore the stock has large upside.”

### Method verdict

```text
PROSPECTIVE DISCRIMINATION = AVAILABLE
```

This supports the Decision Hygiene rule:

> A model correction should improve retrospective fit **and** create future observations that distinguish it from the superseded interpretation.

---

## 11. Pre-expectation / expectation / price separation

The historical case also shows why expectation and price should remain downstream challengers.

The initial attraction to CNY55 risked becoming a circular process:

```text
large assets + high H1 earnings
→ infer fair earnings
→ see CNY55 as attractive
→ attraction increases confidence in the earnings bridge
```

A cleaner process would be:

```text
PIT-bound company / commodity records
→ Reference Frame
→ causal earnings worlds
→ pre-expectation Fundamental View
→ published expectations / market narratives
→ anchoring audit
→ post-expectation Fundamental Belief
→ price-compatible worlds
→ Odds only if probability is established
```

The historical retrospective did not contain enough evidence to establish a decision-grade numerical probability distribution.

Therefore price around CNY55 should have remained:

> **a challenger asking what world must be true**, not evidence that the favorable world is more likely.

---

## 12. Research completeness vs Odds readiness — negative-control read-through

The corrected Xiamen Tungsten research reached a useful state even after confidence fell.

It knew:

- the proper first-order driver;
- the correct integrated cyclical reference frame;
- why the previous normalization was invalid;
- why project mature-state earnings could not be pulled forward mechanically;
- the critical unresolved structural proposition;
- the future evidence that would discriminate it.

What it did **not** know was a qualified cardinal probability distribution.

A Decision Hygiene Human Surface could have said:

> **Current research has identified long-run tungsten price and resource self-sufficiency as the load-bearing variables. The original H1 annualization / impairment-normalization thesis mixed incompatible commodity regimes and is rejected. Future-project value depends on ownership, quota, capex, timing and through-cycle economics. The remaining structural thesis is testable but not probability-qualified at the current PIT. No numerical Odds should be produced from an arbitrary terminal distribution; wait for evidence that maps same-price resource self-sufficiency into attributable cash returns.**

That is a mature research result.

It does not need an expected-value number to be useful.

---

## 13. Failure-attribution stack — what Decision Hygiene adds

Without the new distinctions, the old retrospective could be summarized vaguely as:

> “The research assumptions were too optimistic.”

That loses the causal anatomy of the failure.

Decision Hygiene produces a more useful stack:

```text
PRIMARY FAILURE
Reference Frame Failure
- integrated commodity-cycle economics were not explicit enough

DOWNSTREAM FAILURE 1
Inference Failure
- high-price H1 earnings were mixed with lower long-run-price assumptions

DOWNSTREAM FAILURE 2
Probability Failure / Theater
- exact weights appeared before driver states and dependencies were established

DOWNSTREAM FAILURE 3
Valuation / Timing Failure
- mature future project earnings were translated too directly into present value

UNCERTAINTY-HYGIENE FAILURE
- permit / quota / capex / ownership / ramp uncertainties were compressed into successful mature-state economics

NOT PRIMARY
Evidence Failure
Classification Failure
Exogenous Surprise
```

This hierarchy matters because the corrective action differs by failure type.

- Evidence Failure → improve acquisition / verification.
- Classification Failure → improve source admissibility.
- Reference Frame Failure → re-underwrite the whole causal model.
- Inference Failure → fix transmission logic.
- Probability Failure → stop forcing cardinal weights.
- Valuation Failure → fix time / capital / terminal translation.

The negative control therefore **does** validate practical attribution value from the new cognitive map.

---

## 14. What this control does NOT prove

This control cannot prove that separating Research completion from Odds readiness improves realized investment returns.

Why:

```text
Historical Human Decision = NONE
Historical Action = NONE
Historical Outcome = NONE
```

There is no honest basis to say:

- the Human would have bought;
- the Human should have bought;
- the Human avoided a loss;
- the Human missed a gain;
- the old probabilities caused a bad trade.

Any such claim would violate the anti-hindsight standard the system is trying to create.

Therefore:

> **This is evidence that Decision Hygiene improves diagnosis of research-process errors, not evidence that the Kernel Constitution should already be changed.**

---

## 15. Cross-case evidence after four dogfoods

### YTO — franchised logistics / policy-sensitive network

```text
Research complete enough to stop
Probability NOT ESTABLISHED
Odds withheld
```

### GigaDevice — cycle-amplified fabless platform

```text
Research complete enough to stop
Ordinal / tail probability PARTIALLY ESTABLISHED
Cardinal distribution NOT ESTABLISHED
Odds withheld
```

### Sanhua — stable industrial core + optionality

```text
Research complete enough to stop
Core probability structure materially stronger
Exact core weights not fully calibrated
Optionality probability NOT ESTABLISHED
Total-company distribution NOT ESTABLISHED
Odds withheld
```

### Xiamen Tungsten — historical research-error negative control

```text
Research process initially generated probabilities too early
Wrong / incomplete Reference Frame contaminated inference
Future mature-state valuation was pulled forward too easily
Corrected research became more useful while conviction fell
Probability at corrected PIT = NOT ESTABLISHED
Human Decision / Outcome = unavailable, so decision-error control remains unsatisfied
```

### Combined learning

Four cases now support a narrower, stronger proposition than “markets are uncertain”:

> **The amount and location of probability knowledge varies by economic object. Research can be complete while cardinal probability is absent, partial, or better supported only for a subset of the business. Requiring one complete terminal probability measure can hide those differences and can create probability theater.**

The negative control further shows that this is not only a stylistic preference: in Xiamen Tungsten, premature probability was downstream of a real model-class failure and made an incomplete thesis look more decision-ready than it was.

---

## 16. Constitution-review threshold — current status

The evidence is now strong enough to **open a Constitution design review intellectually**, but not to merge a Constitution change.

### Evidence supporting review

- three different live economic species repeatedly separate Research completeness from cardinal-probability readiness;
- the three live cases show different degrees / locations of probability knowledge rather than one generic refusal to quantify;
- one historical self-correcting case demonstrates that forced / premature probability can mask a genuine Reference Frame failure;
- mature Human-facing research remains useful when Odds are withheld.

### Missing evidence before code change

The strongest negative-control requirement remains unmet:

```text
frozen Human investment judgment
+ later realized outcome
+ strict PIT reconstruction
+ adjudicated decision error or non-error
```

The current repositories do not provide a clean eligible case.

Therefore:

```text
CONSTITUTION DESIGN QUESTION = OPEN / SERIOUS
CONSTITUTION CODE CHANGE = NOT AUTHORIZED
SCHEMA CHANGE = NOT AUTHORIZED
ODDS POLICY CHANGE = NOT AUTHORIZED
```

This is intentional restraint, not unfinished work.

---

## 17. What should happen next

Do **not** manufacture a historical negative control.

The next legitimate routes are:

1. use a future naturally occurring case with a frozen Human Decision and later outcome; or
2. if the Human later identifies a genuine historical investment judgment with recoverable PIT evidence and an adjudicable outcome, reconstruct that case strictly; or
3. continue accumulating prospective Research-complete / probability-readiness dogfoods without changing Constitution.

Until then, the live production contract remains unchanged.

---

## 18. Source register

### Historical Decision OS source

- `auguspp/decision-os/docs/cases/xiamen-tungsten-research-retrospective.md`
  - frozen research retrospective recorded 2026-08-22;
  - explicitly states Human Decision / Action / Outcome pending;
  - documents the early normalization story, missing tungsten-price driver, premature probabilities, project-maturity/timing issues, integrated-cycle transmission issues and the corrected thesis.

### Decision Kernel method / comparison sources

- `docs/decision-hygiene-method-note-2026-09-03.md`
- `docs/dogfood/yto-decision-hygiene-zero-schema-2026-09-03.md`
- `docs/dogfood/gigadevice-decision-hygiene-zero-schema-2026-09-03.md`
- `docs/dogfood/sanhua-decision-hygiene-zero-schema-2026-09-03.md`

No later stock-price outcome is used in this negative control.

---

## 19. What this does not authorize

This dogfood does not authorize:

- a `RESEARCH_COMPLETE` Kernel state;
- a probability-readiness enum;
- Research World schema;
- changing `ResearchSnapshot` probability requirements;
- changing `Scenario` semantics;
- a new failure-attribution state machine;
- a new price-implied-expectation engine;
- live Odds policy changes;
- retrospective Human decision labels;
- any investment authority.

The system should continue to preserve the current Constitution while treating the Research-complete / Odds-ready distinction as a serious, evidence-backed design question awaiting one more class of evidence: an honest Human-decision/outcome negative control.