# Xiaohongshu Writing Harness v1

Status: **DOGFOOD / DOWNSTREAM PUBLISHING / NO INVESTMENT AUTHORITY**

## Objective

Turn one frozen Decision Kernel Research package into a reusable writing harness for one Xiaohongshu investment note without redoing the research and without allowing publication prose to rewrite investment truth.

```text
DeepResearchPackage
        ↓
explicit PUBLIC_SAFE claim selection
        ↓
PublicationBrief
        ↓
Planner prompt
        ↓
Draft prompt
        ↓
Judge / rewrite prompt
        ↓
local hard-gate lint
        ↓
Human final edit / publish
```

Publishing remains downstream:

```text
Research / Evidence / Odds
          ↓
      Publishing

Publishing ─X→ Research
Publishing ─X→ Odds
Publishing ─X→ Human Decision / Action
```

## Why a harness instead of one large prompt

A short GitHub review of mature LLM tooling points in the same direction:

- DSPy treats language-model work as modular programs rather than prompt craftsmanship. The useful lesson here is stage separation: plan, draft, judge.
- Promptfoo treats prompts and models as things that should be regression-tested, compared, and run in CI. The useful lesson here is to keep a stable evaluation rubric instead of judging every draft from scratch.
- Schema-first structured-output tools show the value of forcing intermediate artifacts into explicit contracts. In this harness, the durable object is `PublicationBrief`, not free-form prose.

The harness deliberately does **not** add DSPy, Promptfoo, a model SDK, or another orchestration framework as a dependency. Decision Kernel only borrows the design lessons.

## Source-of-truth boundary

`build_publication_brief(...)` accepts one exact `DeepResearchPackage` and one explicit `PublicationAuthoringInput`.

Every selected factual or market-context claim must:

1. exist verbatim in the frozen Research package;
2. preserve its Research claim kind;
3. retain its exact EvidenceArtifact ids;
4. use only evidence explicitly marked `PUBLIC_SAFE` for this publication.

Unselected evidence defaults to non-publishable. A claim using `REVIEW_REQUIRED` or `DO_NOT_PUBLISH` evidence fails closed.

The authoring overlay may add editorial fields such as `reader_tension`, `strongest_counterpoint`, and `editorial_verdict`, but those remain publication opinion. They do not acquire Research authority.

`human_state_policy` is fixed to:

```text
OMIT
```

The drafting and lint layers therefore cannot publish or infer Human Decision, Action, position, cost basis, or private portfolio state.

## What the historical high-read samples changed

The calibration policy is based on five Human-provided published notes:

| sample | visible engagement in supplied screenshots | reusable tension |
| --- | --- | --- |
| 云南锗业 / 磷化铟 | 146 likes / 89 saves / 116 comments / 63 shares | shortage can be real while duration is still over-priced |
| 亨通光电 / 58元 | 156 / 100 / 159 / 69 | a company can improve while cyclical profit is mistaken for permanent identity change |
| 兆易创新 / 48.5亿 | 145 / 123 / 106 / 41 | high earnings and a high multiple must be tested as two simultaneous assumptions |
| 东山精密 / 201元 | 117 / 63 / 105 / 48 | the price can stay still while new evidence raises the credibility of higher-profit paths |
| 生益科技 / 3213亿 | 127 / 96 / 113 / 19 | SOTP plus implied earnings exposes how many future good things the price already requires |

The main lesson is not a tone adjective. It is a recurring reasoning move:

> **Do not write the company. Audit the assumption embedded in the current price.**

The style policy therefore stores both structural fingerprints and short sentence-level rhythm references from the Human's actual notes. This is intentional: abstract style labels alone produced generic AI research prose in dogfood.

## Three-stage writing program

### 1. Planner

The planner cannot write prose. It must return a JSON plan with:

- 3–5 title candidates;
- one sentence the entire article is trying to prove;
- one job per card;
- exact Research claims used by each card;
- the turn that moves the reader to the next card;
- final answer to the title question;
- the unresolved uncertainty that must remain unresolved.

This is the main anti-report-dump control.

### 2. Drafter

The drafter receives only:

- the `PublicationBrief`;
- planner JSON;
- the selected Human writing fingerprints;
- publication-safe claim ledger.

It is explicitly instructed to:

- open from contradiction, not company background;
- surface the price-implied requirement in the first 20%;
- use numbers only for reverse reasoning, causality, or scenarios;
- represent the strongest counterpoint fairly;
- make a real preferred judgment when evidence supports one;
- preserve FACT / MARKET_CONTEXT / INFERENCE / ASSUMPTION distinctions;
- end with both an answer and one remaining evidence gap.

### 3. Judge / rewrite

The judge uses a stable 10-item rubric:

1. single tension;
2. price implication;
3. fact discipline;
4. causal chain;
5. reverse reasoning;
6. strongest counterpoint;
7. Human voice rather than AI report voice;
8. numerical economy;
9. clear verdict;
10. authority boundary.

Three conditions are hard failures:

- unsupported company facts or inference upgraded to fact;
- Human-state leakage / transaction instruction;
- failure to answer what the current price requires to be true.

## Local hard gate

`lint_publication_draft(...)` is intentionally mechanical and small. It currently flags:

- first-person private portfolio state;
- buy/sell/add/reduce commands;
- generic research-report headings;
- pathological draft length.

The local linter is not a style scorer. Semantic writing quality belongs to the judge stage.

## Reusable CLI

```bash
python -m decision_kernel.publishing \
  --research research_cases/002050-sanhua-deep-research-v1.json \
  --input dogfood/publishing/002050-sanhua-36_3-authoring.json \
  --output /tmp/sanhua-xhs-harness.md
```

The output contains the exact `PublicationBrief` plus planner, drafter, and judge prompts. Any capable model can run those stages; the repository is not tied to one provider.

## Sanhua dogfood

The first fixture is:

```text
dogfood/publishing/002050-sanhua-36_3-authoring.json
```

Its title question is:

> 跌跌不休的三花智控，36.3元贵不贵？

Its intended tension is not "三花是不是好公司" or "机器人空间有多大". It is:

> **36.3元到底还要求核心业务质量、新业务商业化和未来利润中的哪些东西成立？**

The price `36.3` is marked as a Human-provided publication anchor and must be verified against live market data before publishing. It is not silently promoted into frozen Research.

The selected calibration samples are 亨通光电、兆易创新、生益科技 because their structures are closest to the Sanhua question: repricing, reverse earnings requirements, and already-paid-for optionality.

## Explicit non-goals

v1 does not add:

- model provider SDKs;
- automatic prompt optimization;
- Xiaohongshu login or posting;
- scheduled content generation;
- viral scoring or growth automation;
- comment scraping;
- automatic use of engagement as Research evidence;
- Human Decision / Action publication;
- a new investment framework.

The acceptance question is simple:

> **Can a new case reuse frozen Research and Human writing calibration to produce a draft that needs editing, not rewriting from zero?**
