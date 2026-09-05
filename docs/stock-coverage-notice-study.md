# Frozen stock coverage: original notices, not automatic eligibility

Status: BOUNDED PUBLIC-ONLY SOURCE PROFILE / NINE ORIGINALS REVIEWED / ONE AMBIGUOUS SELECTION / NO PRODUCTION DATA ACCEPTANCE.

Actual run `33966231127` retained nine PDFs using twenty public requests and remained INCOMPLETE_SOURCE_STUDY because 603448 returned two equally dated matching notices. Original-source interpretation, exact hashes, page references and review limits: `docs/stock-coverage-originals-proof-2026-09-05.md`. This result does not overwrite the original frozen stock differences or close every coverage question.

## Why this slice

The frozen run `33959190974` has nineteen identities both missing their latest dump bar and lacking a priced snapshot, plus `920289.BJ` with a latest bar but no previous bar. A null quote cannot establish suspension, delisting, a future listing, or a data error. The retained company-action study did not resolve these distinct coverage questions.

Reuse the existing `stock_field_source_study.py`, Requests transport, report/hash/file validation and `adapters/cninfo.py` announcement-page normalization. Do not add a downloader, parser, adjustment engine, review queue or workflow. The existing study workflow now executes the public-only `coverage-notices` profile and no longer exposes the HiThink credential. Its default CLI event-sample mode remains available explicitly, with the old plan shape preserved; it is not re-executed by this workflow.

## Exact bounded source samples

The ten named search leads below are intersected with the actual frozen gap set. They are not status labels or a new universe. All unqueried gap codes remain in the plan.

- Suspension-notice leads: 000016.SZ, 002731.SZ, 002870.SZ, 002998.SZ, 301139.SZ, 301266.SZ, 600929.SH, 688432.SH.
- Listing-notice leads: 603448.SH and the missing-previous-bar case 920289.BJ.

The keyword mapping is fixed in code. It reflects targeted document searches, not proof that each lead is correct. A source query with no result, ambiguous latest originals, absent publication metadata, more results than its one-page window, mismatched stock/org identity or untrusted PDF URL remains incomplete. Do not treat an empty result as no suspension or no listing.

At most one organization-directory GET, ten exact-code/date-window POSTs and ten original-PDF GETs occur: at most 21 requests, within the unchanged global budget of 24. No event query, price query, market dump, automatic pagination or retry is used. Original HTTP body bytes and actual request/completion clocks remain retained. Unsupported responses remain visible.

Each query spans the existing twenty-calendar-day window ending on the frozen comparison date. The full query response is retained. The uniquely latest matching announcement in that window is chosen solely as a source-review sample. Same-time ties are rejected instead of breaking them by identifier. This choice is not proof of the latest effective trading status: a later resumption notice outside the matching title family could exist, or the selected notice may describe a later effective date. Read the original and establish the applicable interval separately. Date-only publisher metadata is not an exact publication clock or historical system availability.

## How to read the result

A successful capture means `CAPTURE_COMPLETE_REVIEW_REQUIRED`, not "all missing stocks explained". The original `DIFFERENCES_REQUIRE_REVIEW` and `production_qualification=NOT_ESTABLISHED` remain unchanged.

Record per exact code which original statement, effective date and page supports an interpretation. Separate:

1. an announced first trading date from presence in a provider's current symbol directory;
2. a suspension in progress from a final delisting decision;
3. a missing first-day previous bar from a zero return;
4. an unresolved or unqueried identity from an excluded identity.

Do not rewrite raw prices, forward-fill, alter the original denominator, or create historical membership breadth. The existing checker and all nineteen missing identities plus the previous-bar case are retained even when a documentary explanation is found. Source evidence supports a later explicit data-contract decision; collection itself makes none.

## Remaining large turnover question

This profile does not reacquire the fifteen event records or two previously reviewed dividend PDFs. It also does not claim to fetch the BSE's actual block-trade rows. The official BSE 2026 trading-rule publication, reviewed via primary-domain indexed text, states that block trades do not enter immediate quotes/index calculation and their volume enters the security's daily total after block trading (section 3.6.8):
https://www.bse.cn/jygl_list/200028217.html

That rule is relevant context, not the missing per-trade evidence or HiThink's cross-endpoint amount/precision contract. The current local/browser transports did not obtain original BSE transaction-page bytes. The large outlier remains unresolved; no third-party quotation is substituted or empirical rounding/tolerance adopted.

## Invocation and evidence retention

```bash
python -m decision_kernel.runtime.stock_field_source_study \
  --profile coverage-notices --frozen /exact/frozen-stock-comparison \
  --output /new/isolated-coverage-capture
```

The CLI verifies the exact source report and original four input hashes before any acquisition. It ignores the HiThink environment credential for the public-only profile. The retained workflow preserves its fresh-main guard, narrow push trigger, read-only permissions, 90-day artifacts, failure exit and offline integrity step. A code merge deliberately performs one bounded changed-profile probe. Documentation-only updates must not trigger another source collection.

No new dependency, workflow, schedule, production state/cache/ledger write, detector change, company posture change or authority change. SHADOW OBSERVATION ONLY. HUMAN ATTENTION AUTHORITY = NONE. RESEARCH AUTHORITY = NONE. INVESTMENT AUTHORITY = NONE.
