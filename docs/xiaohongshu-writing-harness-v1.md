# Xiaohongshu Writing Harness v1

Status: dogfood

This is a **publishing harness downstream from frozen Research**. It is not part of Kernel investment authority, does not create Research truth, does not make investment decisions, and does not publish automatically.

```text
Frozen DeepResearchPackage
        |
        v
explicit PUBLIC_SAFE claim selection
        |
        v
XiaohongshuWritingBrief
        |
        +--> planner prompt --> structured XiaohongshuPlan
        |
        +--> draft prompt   --> structured XiaohongshuDraft
        |
        +--> deterministic validator
        |
        +--> judge prompt   --> revision / human edit
        |
        v
human-controlled publication
```

## Why a harness instead of one large prompt

A short GitHub survey informed the design:

- **DSPy**: treat LM work as modular programs with explicit signatures instead of prompt strings as the unit of architecture.
- **Promptfoo**: keep prompts and model outputs regression-testable rather than relying on one good interactive run.
- **Instructor**: use schema-first structured outputs and validation so downstream stages fail closed on malformed state.
- **STORM**: separate pre-writing/planning, drafting, and polishing/evaluation instead of asking one generation to research, structure, write, and self-edit at once.
- **DeepEval**: treat qualitative LM behavior as an eval problem with explicit dimensions, while preserving deterministic checks for what can be checked mechanically.

The harness adopts those useful ideas without importing their frameworks. Decision Kernel already has Pydantic, frozen Research identity, Evidence lineage, and pytest. v1 therefore stays provider-agnostic and dependency-light.

## What the historical notes changed

The earlier Publisher profile was based on an abstracted style summary. The supplied historical notes add enough direct calibration to replace several weak heuristics.

The sample bank currently includes distilled lessons from:

- 亨通光电 — expectation repricing / identity reconstruction;
- 云南锗业 — shortage duration / industry odds;
- 兆易创新 — normalized earnings / peak-profit discipline;
- 东山精密 — same price, new evidence, higher credibility of an earnings path;
- 生益科技 — SOTP plus implied earnings, with certification/order/profit proof ladder;
- 德明利 — negative calibration: too many top-level research questions weakens the publication tension.

The raw screenshot text is **not** required at runtime. The harness keeps reusable writing lessons and failure modes in package data so the writing system is calibrated without turning the repository into a screenshot archive.

### Frozen publication lessons

1. **One note = one reader tension.** Multiple numbered sections are fine when they advance the same tension.
2. **The title exposes a concrete contradiction or valuation question.** It should create an information gap rather than summarize the answer.
3. **Open with why the question exists now.** Earnings, price, valuation, or new Evidence should collide early.
4. **Reconstruct what the price was or is asking the company to prove.** This is often more useful than asking whether the company is simply "good".
5. **Mechanism before dense numbers.** Numbers are used to prove a causal mechanism, not to display research volume.
6. **Separate profit level from profit durability.** Peak/cyclical/repricing profits cannot automatically inherit a long-duration multiple.
7. **Use a proof ladder for new businesses:** capability -> demand -> order -> revenue -> margin -> durable profit.
8. **"This proves A, but not yet B" is a core move.** Certification, capacity and product availability are not the same thing as repeatable economic value.
9. **A judgment may change even when price does not.** New Evidence can raise or lower the credibility of a future earnings path.
10. **End on the hardest remaining proof.** No BUY/SELL call and no Human portfolio state.

The old "maximum three sub-questions" rule is retired. The direct historical examples frequently use 4–6 numbered tests while still preserving one top-level tension. v1 targets 7–13 cards because that better matches the supplied long-form notes; this remains a publication heuristic, not a Kernel invariant.

## Authority boundary

The harness is deliberately asymmetric:

```text
Research may feed Publishing.
Publishing may not rewrite Research.
```

The authoring spec must explicitly select Research claims as `PUBLIC_SAFE`. Unselected claims are absent from the planner/drafter context.

Facts and market-context claims preserve Evidence lineage. A derived number must be declared as a `DERIVATION` claim whose inputs are already selected public claims. The drafter is instructed not to invent arithmetic.

Human Decision / Action / position / cost basis are always omitted. A current market price may be injected as an explicit market anchor with its own observation time and source reference; it does not mutate the frozen Research PIT.

## Writing is also an adversarial compression test

Publication is downstream, but it is not epistemically useless to Research.

A good note compresses a large research package into one reader tension, usually forcing explicit answers to questions such as:

- what does the current price actually require;
- what is already proven versus merely plausible;
- whether a consensus earnings number already contains the optionality being discussed;
- whether the same narrative is being rewarded in both earnings and the valuation multiple;
- which one assumption carries the optimistic case.

That compression can reveal a defect that was easy to miss inside a long research package.

The correct loop is:

```text
Frozen Research
→ Writing / price reverse-engineering
→ unsupported bridge exposed
→ Research Challenge
→ re-underwrite Research
→ freeze new Research if earned
→ rebuild the publication brief
```

The wrong loop is:

```text
Frozen Research
→ draft is hard to make coherent
→ invent a cleaner number / bridge in prose
→ silently upgrade Research
```

**If the note cannot answer its headline question without smuggling in a guessed earnings scope, valuation input, probability, or causal bridge, stop polishing. The writing run has found a Research gap.**

Typical challenge signals are defined in `docs/full-research-review-gate-v1.md`, including ambiguous core earnings, underwritten valuation inputs, optionality double counting, market-expression mixing, proof-ladder gaps, and false precision.

A writing-originated challenge is an attention signal only. Publishing still cannot mutate Belief, Odds, Human Decision, or Action.

This is a deliberate purpose of the harness: publication should make the research easier to audit, not merely easier to read.

## Provider-agnostic workflow

Build a brief and planner prompt:

```bash
python -m decision_kernel.xiaohongshu_harness build \
  --research research_cases/002050-sanhua-deep-research-v1.json \
  --authoring eval/xiaohongshu/002050-sanhua-authoring-v1.json \
  --output-dir /tmp/sanhua-xhs
```

Send `planner-prompt.txt` to the model of choice and save its strict JSON output as `plan.json`.

Render the drafting prompt:

```bash
python -m decision_kernel.xiaohongshu_harness draft-prompt \
  --brief /tmp/sanhua-xhs/brief.json \
  --plan /tmp/sanhua-xhs/plan.json \
  --output /tmp/sanhua-xhs/draft-prompt.txt
```

Save the model's structured draft as `draft.json`, then run deterministic checks:

```bash
python -m decision_kernel.xiaohongshu_harness validate-draft \
  --brief /tmp/sanhua-xhs/brief.json \
  --draft /tmp/sanhua-xhs/draft.json \
  --markdown /tmp/sanhua-xhs/draft.md
```

Render a judge prompt for qualitative evaluation:

```bash
python -m decision_kernel.xiaohongshu_harness judge-prompt \
  --brief /tmp/sanhua-xhs/brief.json \
  --draft /tmp/sanhua-xhs/draft.json \
  --output /tmp/sanhua-xhs/judge-prompt.txt
```

## Deterministic checks vs LM judge

Deterministic checks block what can be known mechanically:

- plan/draft claim ids outside the publication brief;
- upgrading a Research inference into a publication FACT;
- undeclared DERIVATION arithmetic;
- Human Decision/Action/position leakage patterns;
- explicit recommendation language;
- reader-tension drift;
- malformed structured output.

The LM judge evaluates what is genuinely semantic:

- single-tension coherence;
- title information gap;
- opening pull;
- causal mechanism;
- implied-expectation clarity;
- proof-ladder discipline;
- scenario discipline;
- treatment of counter-evidence;
- voice and pacing;
- whether the draft is papering over a Research gap that should be challenged instead of polished.

This split is intentional: semantic style judgment can be soft, but Research identity and publication authority stay hard.

## v1 stop rule

Do not add model routers, auto-publishing, engagement prediction, title A/B optimization, vector style retrieval, or a second Research schema yet.

First dogfood the harness on real frozen cases (starting with Sanhua), compare drafts against the historical references, and collect actual publication outcomes. New machinery must be earned by observed failure.
