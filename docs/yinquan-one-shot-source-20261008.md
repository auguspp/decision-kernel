# YinQuan 14-stock historical source — isolated one-shot

Scope: Human-approved one-time isolated research source capture, not a new
market provider, recurring job, research route or investment action. Exact
cohort: the 14 user-supplied YinQuan DAT identities (not uploaded here).
Fixed interval 2023-01-01 to 2026-09-30, selected to permit 441-trading-bar
warm-up for nested 89-day HHV filters. Review signals from 2025 onwards.

Reuse Decision: **REUSE + THIN_ADAPTER**. Reuse existing
tushare_relay._http_get fixed-host HTTPS, secret, no-redirect, byte,
reflection and timeout guards. The existing Relay explicitly allows daily
and daily_basic. The existing C2 price-check is fixed to a different frozen
cohort and 61 sessions; do not change/replay that completed pilot. No new
SDK, secret, scheduled source capture, database or provider fallback.
No third-party source code is copied.

After standard PR/full CI and independent exact-main CI, one manual run
from current main with its exact SHA. Preflight requires the workflow's
unique one-shot attempt, current main and latest successful current main
CI. Source key first appears only in the subsequent isolated capture step.
At most 28 HTTPS requests: daily and daily_basic for 14 exact names; one
attempt each; hard stop on first refusal, unknown response or timeout. No
source retry, no FTShare/HiThink fallback, no all-market call.

Save exact raw responses, query identities, hash, clocks, failure checkpoint,
normalized CSV and coverage only to one 30-day Actions artifact, never
the read-model, Git source tree, Brief, News, Quick, Watch or Sites. Verify
the artifact from retained bytes with no credentials and no network requests.
Raw vendor data are retained only under the existing source-use boundaries;
do not redistribute an artifact as a public price dataset.

This is today's historical retrieval, not dated source availability.
Relay is a third-party gateway; underlying official Tushare identity,
turnover_rate versus Tongdaxin HSL equality, PIT signal appearance,
price adjustment and execution fills remain **NOT ESTABLISHED**. DAT
samples are retrospective snapshots, not proof of live historical signals.
A completed capture is not a backtest result or predictive hit rate.

Offline in the original ChatGPT research workspace: join the 14 original
user DAT files to saved provider CSV by exact symbol and market date, using
the existing YinQuan offline replay; no DAT are uploaded to GitHub. Test
green persistence and green+yellow bright with mature T+5/10/20 dates.
If capture is incomplete, report the actual partial status, not no signal.

Exit: remove the manual workflow, thin capture and tests via ordinary PR
after study, retaining original run/PR receipts and consent. No repeated
dispatch under this authorization.
