# AlphaAnalyst Claim-Audit Code Diligence — 2026-09-03

Status: **EXTERNAL CODE DILIGENCE / DOCS-ONLY / NO DEPENDENCY / NO KERNEL CHANGE**  
External repository: `kbhujbal/AlphaAnalyst-open-source-autonomous-equity-research-agent`  
Reviewed public commit lineage: repository `main` around commit `2cf3d4ee6c99ed8aee9871710825d25aca30e687` as surfaced by GitHub code search  
Recorded: **2026-09-03**

## 0. Purpose

This review does not ask whether AlphaAnalyst is a good stock-picking system.

It asks a narrower engineering question:

> **What mechanical source / number / citation controls are actually implemented, which ones are worth borrowing for Decision Kernel Claim Audit, and where does AlphaAnalyst stop at citation correctness rather than epistemic warrant?**

The review follows four traces:

```text
source number
-> normalized fact / finding
-> derived number
-> final memo citation
```

and inspects failure semantics:

```text
missing source
wrong / unknown source tag
number without source tag
source disagreement
unsupported citation snippet
source exists but is inadmissible for the claim
```

This note does not add:

- an external dependency;
- a new citation schema;
- a new confidence score;
- a new provider abstraction;
- a new Research lifecycle;
- any copied AGPL / licensed implementation;
- any Kernel Constitution change.

---

## 1. Executive verdict

The README design claims are substantially reflected in code, but with important limits.

### Confirmed implemented mechanisms

1. **Pure-Python DCF arithmetic using `decimal.Decimal`.**
2. **Pydantic schemas for agent findings, citations and final memo output.**
3. **Programmatically assigned fact tags (`F1`, `F2`, ...).**
4. **Final synthesizer rejects / downgrades memo sections containing unknown tags.**
5. **Final synthesizer downgrades any section containing numerical content with no source tag at all.**
6. **Final citation list is derived programmatically from tags actually used in memo prose.**
7. **Some fundamental fields are cross-checked between FMP and EDGAR; EDGAR wins when both are available, with divergence recorded.**
8. **Valuation arithmetic is deterministic once numeric inputs are built.**

### Important gaps

1. The final validator checks **tag existence**, not whether each numerical claim is supported by the cited fact.
2. A section with several numbers and only one valid tag passes the validator.
3. Citation snippets produced by LLM agents are not mechanically checked against the cited source chunk.
4. Filings `page_hint` is a retrieval-chunk ordinal, not clearly a true filing page coordinate.
5. The synthesizer collapses each multi-source Finding to the **first evidence item**, losing part of source lineage.
6. DCF / fundamentals facts are re-labeled generically as `source_type="fact"` with synthetic IDs, even when a richer provider `Source` object exists upstream.
7. The citation model records source type / ID / snippet, but not **assertion scope**, epistemic role, derivation lineage, PIT admissibility, or whether the source has authority for the claim.
8. LLM-generated news sentiment is converted deterministically into DCF growth / margin / WACC adjustments. The LLM does not perform the arithmetic, but it does provide a numerical judgment that enters valuation.
9. A valid citation can therefore still be epistemically wrong: `citation correctness != source admissibility`.

### Bottom line

> **AlphaAnalyst has several good fail-closed mechanical guardrails worth borrowing as harness patterns, but its final citation validator is materially weaker than Decision Kernel's desired Claim Audit semantics.**

The best borrowing target is **mechanical integrity**, not its epistemic model.

---

## 2. Finding / citation data model

AlphaAnalyst defines:

```python
class Citation(BaseModel):
    source_type: Literal[
        "filing", "transcript", "news", "fact", "price", "macro", "estimates"
    ]
    source_id: str
    snippet: str

class Finding(BaseModel):
    claim: str
    evidence: list[Citation] = Field(min_length=1)
    confidence: Literal["high", "medium", "low"]
```

Useful properties:

- a Finding cannot exist with zero evidence;
- source categories are explicit;
- source identifier and snippet travel with the claim;
- schema validation is cheap and deterministic.

But the model does not express the semantic distinctions already present in Decision Kernel Research Method v2:

```text
source fidelity
-> epistemic warrant
-> belief integration
```

Missing dimensions include:

- `PRIMARY_REALIZED` versus `PRIMARY_STATEMENT`;
- `MARKET_EXPECTATION` versus `ANALYST_MODEL` versus `ANALYST_OPINION`;
- `REALIZED_OUTCOME` versus `ATTRIBUTED_STATEMENT` versus `MODEL_FORECAST`;
- derived versus reported values;
- the causal claim a source is allowed to support;
- whether a source is contemporaneously available at the Research PIT.

Therefore the AlphaAnalyst `Citation` object is closer to:

> **source attachment**

than to:

> **claim admissibility proof**.

### Confidence field caution

`Finding.confidence` is `high / medium / low`, but code inspection here did not find a formal evidence-calibration contract that makes those labels Decision Kernel-compatible.

Decision Kernel should not borrow this field merely because it is typed.

---

## 3. Filings extraction — good source restriction, weak citation verification

The filings agent gives the LLM retrieved filing chunks and instructs:

```text
Use ONLY the provided chunks.
Cite every claim with [10-K p.X].
Do not invent facts.
```

The LLM returns:

```python
class _LLMCitation(BaseModel):
    page_hint: int
    snippet: str
```

Then `_to_finding()` maps those responses into `Citation` objects.

### Good properties

- retrieved chunks constrain the context;
- no-citation answers are rejected;
- citations outside the available chunk index do not produce a valid in-range chunk mapping;
- the final Finding still requires at least one citation.

### Important weakness 1 — `page_hint` is not a true page validator

`_format_chunks()` labels retrieved chunks as:

```python
for i, c in enumerate(chunks, start=1):
    ...
    f"[{filing_label} p.{i} source_id={sid}]"
```

So `p.1`, `p.2`, etc. are generated from **retrieval order**.

They are not demonstrated in this code path to be actual document page numbers.

The final `source_id` becomes something like:

```text
10-K <source_id> p.<retrieval-index>
```

Therefore the README language about auditing a number back to a "10-K page" should be interpreted cautiously unless another source coordinate is preserved elsewhere.

### Important weakness 2 — snippet grounding is not checked

The LLM returns `snippet` text.

`_to_finding()` stores:

```python
snippet=c.snippet[:500]
```

but does not verify:

```text
c.snippet is actually contained in cited chunk_text
```

Therefore a citation can point to an in-range retrieved chunk while carrying a fabricated or mismatched snippet.

### Important weakness 3 — claim-to-citation warrant is not checked

Even if the snippet is real, the code does not mechanically prove that it supports the whole claim.

Example failure class:

```text
source says revenue rose 10%
claim says margin expansion proves durable pricing power
citation points to the revenue source
```

Tag / source existence can be valid while epistemic warrant is invalid.

This is exactly the distinction Decision Kernel must preserve.

---

## 4. Synthesizer fact ledger — useful mechanical pattern

The synthesizer builds a finite fact list and assigns sequential tags:

```text
F1
F2
F3
...
```

The final LLM is instructed:

> use ONLY these facts; every numerical claim must cite an `[F#]`.

This is a useful pattern because the synthesizer cannot legally cite arbitrary external material not in the ledger.

### Strong mechanism

The final memo does not trust the LLM-provided `citations` array.

Instead, `_derive_citations()` scans tags actually used in memo sections and programmatically builds the final citation list.

This avoids one common failure:

```text
memo prose uses F7
but LLM forgets to add F7 to citations[]
```

The final citation inventory follows the prose tags rather than trusting a second LLM-generated bookkeeping field.

### Decision Kernel borrowing candidate

> **Programmatically derive the outward-facing citation set from frozen claim/evidence references rather than asking the LLM to maintain a parallel bibliography.**

This is directly compatible with Decision Hygiene.

---

## 5. Final citation validator — fail-closed but only section-level

The final section validator does two checks.

### Check A — unknown tags

If prose contains a tag that is not in the fact ledger:

```text
unknown tags
-> section downgraded to Insufficient evidence
```

Good.

### Check B — numerical content with no tag

If a section contains any number but uses zero tags:

```text
number present
+ no [F#] anywhere in section
-> section downgraded
```

Also good.

Tests explicitly verify these behaviors.

### The critical limitation

The code is effectively:

```python
used = tags_in_section
if has_numbers(section_text) and not used:
    fail
```

It does **not** do:

```text
for each number / numerical clause:
    identify supporting tag
    verify the cited fact contains or derives that number
```

Therefore this would pass:

```text
Revenue was $100B, margin was 90%, EPS was $50 and debt was $1B [F1].
```

as long as `F1` is a valid tag, even if `F1` supports only one of those numbers.

The validator is therefore:

> **section-level source-presence validation**

not:

> **claim-level numeric provenance validation**.

### Failure semantics worth borrowing

When validation fails, AlphaAnalyst does not regenerate repeatedly.

It replaces the affected section with:

```text
Insufficient evidence (synthesizer downgraded — ...)
```

This is a strong Decision Hygiene pattern:

> **fail closed and preserve uncertainty rather than silently repairing unsupported prose.**

Decision Kernel should strongly prefer this behavior over best-effort citation patching.

---

## 6. Multi-evidence lineage is lost in synthesis

A `Finding` can contain multiple evidence items.

But `_build_facts()` does:

```python
primary = finding.evidence[0]
source_type = primary.source_type
source_id = primary.source_id
```

and stores one `_Fact`.

The remaining evidence is not preserved in the final fact ledger.

This creates a lineage-loss problem.

Example:

```text
claim supported by:
- SEC filing
- transcript
- independent industry context

synthesizer fact retains:
- only first citation
```

For Decision Kernel this is undesirable because disagreement / support often depends precisely on **which source roles jointly support a claim**.

Borrow the finite fact ledger pattern, but do not collapse evidence lineage to one citation.

---

## 7. Derived valuation facts lose upstream provenance

`_build_facts()` creates DCF facts such as:

```text
DCF intrinsic value per share
DCF growth rate used
DCF avg FCF margin used
DCF enterprise value
DCF equity value
```

and labels them:

```text
source_type = "fact"
source_id = "dcf-base-case"
```

Likewise `FundamentalSnapshot` fields are turned into `fact` citations with synthetic IDs such as:

```text
fundamentals:<ticker>:<period>
```

But the `FundamentalSnapshot` model itself contains a richer `Source` object with provider / URL / fetched time.

That upstream provenance is not carried through into the final synthesized citation.

### Decision Kernel implication

Derived numbers should retain a graph like:

```text
DERIVED CLAIM
-> derivation function / formula / version
-> exact input claims
-> exact source lineage for each input
-> PIT
```

not merely:

```text
source = fact / dcf-base-case
```

A derived number needs **derivation provenance**, not a fake primary-source identity.

---

## 8. Pure-Python Decimal valuation — genuinely implemented

The DCF module is strong mechanically.

It is explicitly pure Python with no I/O / LLM calls and uses `Decimal` for money math.

It also validates:

- `terminal_growth < wacc`;
- projection years constrained to 3–10;
- non-empty histories;
- positive share count;
- valid positive revenue history.

Sensitivity calculations also use `Decimal`.

This supports the README's arithmetic-engineering claim.

### Borrowing candidate

Decision Kernel already follows Decimal discipline in financial calculations, so this is more external confirmation than new functionality.

The useful general rule is:

> **Semantic Research can be LLM-assisted; arithmetic transformations should be deterministic, typed and independently testable.**

No new Kernel mechanism is required merely to copy this.

---

## 9. "No LLM touches arithmetic" needs a semantic caveat

The arithmetic itself is deterministic, but the valuation is not purely free of LLM numerical influence.

The NewsAgent asks an LLM to assign each article:

```text
sentiment: float in [-1, 1]
```

The pipeline then computes a recency-weighted `net_sentiment` and deterministically maps it into:

```text
revenue_growth_delta = sentiment * 0.005
margin_delta = sentiment * 0.002
discount_rate_premium_bps = -sentiment * 100
```

These adjustments feed DCF assumptions.

So the accurate statement is:

```text
LLM does not perform valuation arithmetic
```

but not:

```text
LLM judgments cannot numerically move valuation inputs
```

### Decision Kernel caution

This is exactly the kind of hidden semantic-to-numeric bridge Decision Kernel should avoid unless explicitly qualified.

A qualitative news classifier should not become a cardinal DCF adjustment merely because the multiplication is done in Python.

Deterministic arithmetic does not cure unsupported cardinal semantics.

---

## 10. Cross-source numeric reconciliation — a useful pattern

The market-data fetcher cross-checks selected fundamentals between FMP and EDGAR.

For fields such as revenue / EPS:

```text
FMP value
vs
EDGAR value
-> relative difference
-> record Divergence
-> choose EDGAR when available
```

A divergence threshold of 1% is logged.

The `FundamentalSnapshot` retains a list of `Divergence` records with:

- field;
- FMP value;
- EDGAR value;
- relative difference;
- chosen source.

This is a useful mechanical pattern.

### Borrowing candidate

Decision Kernel could benefit from a small **numeric source-disagreement audit harness** where multiple admissible source lanes genuinely overlap.

But it should not become a generic provider fallback abstraction.

For production market data, existing policy remains:

```text
HiThink = sole production market-data source
```

The useful borrowing is therefore not "add fallback providers".

It is:

> **When Research has two legitimate records for the same claimed quantity, preserve both values, the disagreement magnitude and the explicit rule used to select / reject one.**

This fits Claim Audit much better than silently overwriting one number.

---

## 11. Citation correctness versus source admissibility

This is the central comparison.

AlphaAnalyst can mechanically answer some of:

```text
Does the memo use a known tag?
Does a numerical section have at least one tag?
Does the Finding have at least one Citation?
Does a source ID exist in the local fact ledger?
```

Decision Kernel needs additional questions:

```text
What epistemic role does the source own?
What assertion scope is allowed?
Is the claim reported, attributed, inferred or modeled?
Was the source available at the PIT?
Does the cited evidence actually warrant this causal claim?
Is a derived number traceable through deterministic inputs?
Does Published Expectation challenge Belief without becoming Fact?
```

Examples:

### Valid citation, invalid epistemic role

```text
sell-side EPS forecast
-> cited correctly
-> used as REALIZED_OUTCOME
```

Citation is correct. Claim Audit must reject the assertion scope.

### Valid source, unsupported causal inference

```text
company reports overseas revenue growth
-> cited correctly
-> claim says overseas incremental ROIC is high
```

Source fidelity is fine. Warrant is missing.

### Valid derived number, lost input lineage

```text
DCF value = $250
-> source_id = dcf-base-case
```

Arithmetic may be correct, but audit still needs the exact assumption / input lineage.

Therefore:

> **Citation validation is necessary but not sufficient for Decision Hygiene.**

---

## 12. What Decision Kernel should borrow

### Borrow 1 — finite frozen fact ledger for synthesis

Before final prose generation, build a finite list of admissible claim / evidence objects.

The writer may cite only those objects.

This reduces free-form source hallucination.

### Borrow 2 — programmatic citation derivation

Do not ask the LLM to maintain the final bibliography.

Derive outward citations from the exact claim / evidence references actually used.

### Borrow 3 — fail-closed section semantics

Unsupported numeric prose should become:

```text
Insufficient evidence
```

or equivalent Decision Hygiene language.

Do not silently patch a source after generation.

### Borrow 4 — deterministic numeric / valuation transforms

Keep formulas outside the LLM.

Already largely aligned with Kernel doctrine.

### Borrow 5 — explicit source disagreement record

When two admitted source records disagree on the same quantity, preserve:

```text
value A
value B
difference
selection / rejection rule
```

Do not hide the disagreement.

---

## 13. What Decision Kernel should not borrow

### Do not borrow 1 — section-level tag presence as "citation validation"

Kernel needs claim-level warrant, not merely one tag somewhere in a paragraph.

### Do not borrow 2 — generic `high / medium / low` confidence

This risks creating a confidence machine without calibrated semantics.

### Do not borrow 3 — primary-evidence collapse

Do not throw away all but the first supporting source.

### Do not borrow 4 — synthetic `fact` provenance for derived values

Derived claims need derivation lineage.

### Do not borrow 5 — LLM qualitative judgments converted automatically into cardinal valuation deltas

A Python multiplication does not make an LLM sentiment score epistemically qualified.

### Do not borrow 6 — broad provider abstraction as a side effect

Especially not for production market data.

### Do not borrow 7 — "different model family = genuine independence"

Model-family diversity may reduce some shared errors but does not prove epistemic independence if agents share data, prompts, framing or priors.

---

## 14. Candidate Claim Audit harness improvements — zero schema first

This review suggests a few **test-harness ideas**, not production schema changes.

### Experiment A — claim-to-source warrant test

Given a Research claim:

```text
claim
+ assertion scope
+ source role
+ source excerpt
```

mechanically / semantically check whether the source role is admissible for that assertion scope.

Example:

```text
MARKET_EXPECTATION
cannot satisfy
REALIZED_OUTCOME
```

This is stronger than citation existence.

### Experiment B — derived-number lineage test

For a derived numerical claim require:

```text
derivation name / formula
input claim IDs
input units
PIT
output value
```

Then verify arithmetic deterministically.

No source should be invented for the derived number itself.

### Experiment C — multi-source preservation test

Ensure a claim with multiple evidence records retains all material evidence roles through synthesis / freeze.

### Experiment D — unsupported numeric-clause fail-closed test

Rather than checking only paragraph-level tags, test whether each material numeric clause has an admissible provenance path.

### Experiment E — source disagreement audit

When two primary / admissible records conflict, freeze the disagreement explicitly rather than selecting silently.

These should be dogfood / harness experiments first.

No Claim Audit schema change is justified by this external review alone.

---

## 15. Final assessment

AlphaAnalyst's strongest engineering contribution is not "six agents" or autonomous equity research.

It is the combination:

```text
finite facts
+ deterministic tags
+ typed final schema
+ fail-closed numeric-source check
+ deterministic arithmetic
+ explicit numeric source divergence
```

That is useful.

But the system currently does not mechanically close the gap:

```text
citation exists
-> citation actually supports this claim
-> source has authority for this assertion scope
-> claim is integrated into Belief appropriately
```

Decision Kernel's Research Method v2 already names that gap more explicitly.

Therefore the external lesson is:

> **Borrow AlphaAnalyst's mechanical audit harness patterns, but keep Decision Kernel's stricter epistemic layers. The next improvement should make admissibility and derivation more machine-checkable without reducing Research to a citation-counting system.**

Frozen recommendation for method development:

```text
ALPHAANALYST DEPENDENCY = NO
ARCHITECTURE COPY = NO
MECHANICAL PATTERNS = YES, SELECTIVELY

HIGHEST-VALUE BORROWING CANDIDATES:
1. programmatic outward citation derivation
2. fail-closed unsupported numeric prose
3. explicit cross-source numeric divergence record
4. deterministic derived-number lineage tests

HIGHEST-VALUE GAP TO PRESERVE:
citation correctness != epistemic warrant != belief integration
```
