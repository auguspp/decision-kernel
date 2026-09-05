# Sector Radar objective outcomes — T+5 / T+20

Status: READ-ONLY HARNESS EVALUATOR / NOT INVESTMENT JUDGMENT / NO SIGNAL AUTHORITY.

## Delivered function

`runtime/sector_radar_outcomes.py` evaluates every existing ledger event at two fixed horizons. It reads the existing strict event ledger, exact daily rolling market states, and an explicit trading calendar. It produces `outcomes.json` and a self-contained Chinese `index.html`. It never generates candidates, changes gates, writes market state, fetches prices, computes investment Odds, accepts Human annotations or settles a Human Judgment.

The input as-of session is explicit and must itself have a supplied verified state. It describes an input boundary, NOT a claim of today's latest data, a trading-calendar freshness certificate or proof of live/prospective provenance. A synthetic ledger with synthetic state can be evaluated in tests; its hashes do not turn it into real prospective evidence. Actual corpus identity must continue to come from original successful runs and audited source artifacts.

The Human's deferred Position/Holding-loop note remains deferred. This evaluator is not that module: it measures sector observation paths, not HOLD/ADD/REDUCE/EXIT decisions or executed returns.

## Outputs and definitions

Each event gets one T+5 row and one T+20 row, including events omitted from the 0–3 display. Horizons count the next five/twenty entries in the supplied calendar, not civil days. A future calendar is not required to report pending; an unknown target date stays null rather than being guessed as the next weekday.

- `PENDING_HORIZON`: all required elapsed day states are present but the fixed horizon has not completed as of the input boundary. No shortened-window metrics are reported.
- `INPUTS_INCOMPLETE`: one or more exact day states, including the signal anchor or maturity day, are absent. The full missing-date list remains visible and no metrics for that horizon are fabricated. A newer 127-day window is not used to impersonate the missing day's original state.
- `EVALUATED`: signal plus all five/twenty forward day states are present, identity/continuity checks pass, and the fixed objective path is measured. This does not mean an investment thesis is true or a judgment was good.

For horizon h and signal-close anchor 0:

```text
sector_return    = sector_close[h] / sector_close[0] - 1
benchmark_return = benchmark_close[h] / benchmark_close[0] - 1
excess_return    = sector_return - benchmark_return
```

MFE/MAE fields are explicitly CLOSE-PATH extrema of the cumulative return at 0..h, including zero at the signal close. MAE is signed non-positive, MFE non-negative. Excess-path extrema use cumulative sector minus benchmark returns at each close. These are not intraday extremes, total shareholder returns, executable fills, strategy returns, transaction-cost-adjusted returns or PnL. A post-close signal could not have been filled retroactively at its anchor close.

The existing homogeneous-family snapshot calculation supplies each day's 20-day rank/rating and the existing persistent/accelerating gate predicates. No new state thresholds are introduced. The report records both predicates, active-day counts excluding the anchor, the consecutive forward prefix during which an originally triggered gate remains active, and its first exit date. If both gates triggered originally, the prefix uses their logical OR, with both separate flags retained. Re-entry after an exit does not extend the original continuous prefix. Positive `rank_20d_change` means rank improvement (signal rank minus horizon rank).

Every objective record retains event ID/hash, original group hash, catalog/benchmark/formula/policy identities, the exact daily state hashes, endpoint closes and per-day ranks/flags. The outcome hash excludes report-generation time, later observations and Human annotations. Extending inputs beyond T+20 cannot change an already complete T+5/T+20 record; a conflicting data revision is rejected instead of being applied silently.

Two horizons are two measurements, not two independent forecasts. Parent and child events keep their original group relationship; the evaluator does not infer new groups, historical memberships or independent decision episodes. No aggregated win rate, opportunity score or optimization objective is created.

## Identity, continuity and time checks

Reuse the existing ledger/state validators and snapshot/entry functions. Every supplied state must be content-hash-valid, completed, on the explicit calendar and recorded no later than generation. Future events/states are refused. Duplicate identical states collapse to one day; conflicting versions require explicit review.

Neighboring supplied windows must retain exact catalog, formula, benchmark, family identities and origin lineage. The rolling window must agree with the calendar. Every overlapping close AND turnover must be identical; validly rehashing a revised observation does not make it acceptable. Missing day states can be listed without silently bridging them; nonoverlapping windows require a separate recovery process.

The event must point to the exact signal-day state hash. Its frozen candidate is reproduced from the original previous/current snapshot pair and compared as a complete candidate, not just by ticker. The evaluator never consults the event ledger to decide a new false-to-true transition. It merely validates the supplied old event's anchor and measures future observations.

There is intentionally no calendar inference from price rows or automatic holiday assumption. The function consumes a normalized explicit calendar; CLI uses the existing HiThink calendar-envelope normalizer. For real use, retain that calendar's original acquisition provenance with the source run audit. Intraday, late-arriving and revised inputs do not acquire earlier observation clocks by being loaded here.

## Usage

With the existing package installed and original files already available locally:

```bash
python -m decision_kernel.runtime.sector_radar_outcomes \
  --ledger ./inputs/candidate-events.json \
  --calendar ./inputs/saved-calendar-response.json \
  --state ./inputs/signal-day-market-state.json \
  --state ./inputs/next-day-market-state.json \
  --as-of 2026-09-08 \
  --output ./objective-review
```

The shown dates and paths are invocation examples, not assertions that such real events or files exist. Repeat `--state` for every day required by the events through the explicit as-of boundary. Use a NEW output directory outside the input directories. Both outputs are new read-only reports; the source ledger, source states and old reports remain unchanged. CLI exits 2 for incomplete inputs while preserving the explicit incomplete report; malformed or conflicting inputs fail before a report is published. No overwrite, discovery, fallback or remote write is implemented. CLI bounds reads to 16 MiB/file and 128 supplied daily states; these are operational limits, not candidate filters.

The 127-day producer state contains prices but does not permanently retain all earlier state identities. Exact daily originals must be preserved independently in existing successful workflow artifacts. The evaluator does not download them, hide their expiry or mint replacement daily state hashes. Old events whose source states are unavailable remain visibly incomplete. Scheduling, automatic archive assembly, durable outcome retention and attaching the evaluator to the producer are subsequent integration work, NOT claimed complete by this PR. No workflow is changed here.

## Reuse-first decision

Reused existing event/state parsing and hash validation, exact previous/current computations, 881/884 ranking, gate predicates and canonical identities. HTML disclosure and escaping use the standard library/native browser. No new dependency, framework, downloader, state store or backtest engine.

Alphalens prior art was revisited: https://github.com/stefan-jansen/alphalens-reloaded and the original forward-return API at https://quantopian.github.io/alphalens/alphalens.html . Its useful separation of signals and forward returns is retained. The original API explicitly warns that forward-return outlier filtering introduces lookahead. We do not import the cleaning/quantile pipeline: our inputs are fixed ledger events, missing states must remain rows rather than dropped factors, exact Decimal and state identity matter, and there is no portfolio/group-neutral-return assumption. We did not copy its implementation. A comprehensive factor-analysis dependency is not necessary to divide two already-qualified prices; it remains a possible offline comparison tool after a real corpus exists.

## Acceptance boundaries

Tests reuse the existing audited end-to-end synthetic producer fixture to create genuine computed 881/884 false-to-true candidates (no mocked selector), then the existing adapter normalizer/appender to form explicit synthetic forward states. They check known returns and extrema, maturity boundaries, independent ranks, persistence, duplicate/no-event handling, missing original day states despite later price coverage, conflicting/rehashed histories, fake candidate/anchor identities, clock boundaries, caller Decimal context, stable mature hashes, CLI files, and no input mutation or network.

These are code tests, NOT a prospective market corpus, a proof of today's provider state, a new workflow run or a real candidate outcome. The actual Sector producer's next completed-session append/replay/context publication remains separately pending. Objective outcomes never accept Human review annotations or govern learning. Current source, signal and authority boundaries remain unchanged.
