# B1 public source families — bounded original capture

2026-09-27. Authority and six-item reuse/scope record: #297 comment5855494088.
This source slice follows #610/#612. It does not claim fixed-R or Sites adoption.

## Exact scope

One manual `radar-global-public` run selects one family and one 14-calendar-date
window ending at most yesterday UTC (within the prior 31 days). No schedule,
source key, account, paid subscription, arbitrary URL/input, redirect, retry or
source fallback. Main/code/independent main CI and attempt 1 are required before
HTTP. An HTTP 401/403/429 or uncertain response stops the rest of that service.
The original Relay, News, Quick Inbox, publisher and Markets are unchanged.

| Family | Fixed source / selected series | Important meaning |
|---|---|---|
| treasury | US Treasury monthly XML; 1m/3m/6m/1y/2y/5y/10y/30y | Annual par yields in percent, changes in bp; not bond price/total return or all global rates. At most two monthly requests. |
| fx | ECB 90-day XML; USD/CNY/JPY/GBP per EUR | Information reference rates, not executable bid/ask; no implicit USD rebasing. One request. |
| commodities | Yahoo chart GC=F/CL=F/BZ=F | Vendor future daily close, not spot or settlement. USD/troy ounce or USD/barrel; exact response symbol/type/currency/timezone required. Contract-roll continuity remains UNKNOWN, so interval returns are not calculated. At most three requests. |
| crypto | Coinbase Exchange BTC-USD/ETH-USD daily candles | That venue only, UTC daily buckets; empty/no-trade intervals not filled. No exchange account, balance or order access. At most two requests. |

## Sources and reuse

Official contracts inspected: Treasury XML feed documentation
(https://home.treasury.gov/treasury-daily-interest-rate-xml-feed), ECB euro reference
rates and its linked 90-day XML
(https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html),
Coinbase product-candles documentation
(https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles).
CME's gold/WTI/Brent specifications provide the quotation-unit convention:
https://www.cmegroup.cn/gold/ ,
https://www.cmegroup.com/cn-s/markets/energy/crude-oil/light-sweet-crude.html ,
https://www.cmegroup.com/cn-s/markets/energy/crude-oil/brent-crude-oil-last-day.html .
This does not upgrade Yahoo into an exchange-original source or certify a contract month.

Reuse Decision: **REUSE existing public HTTP/serialization; THIN_ADAPTER source
protocols**. #508/5773538785 and #511 retained candidates were consumed first;
PIT bars/universes/SEC fundamentals do not supply these four current source families.
OpenBB at `3e071fcc2cd9f891cac6040ae60296dba76dab46`: inspected federal_reserve
`treasury_rates.py` blob `b584d4439d419df2f3278f1ea916c6c783aa3fbc` and yfinance
`futures_historical.py` blob `02bd4de466c798d86720836cd1c04bb298d10244`.
Adopt explicit dates/maturities, unit conversion discipline, unadjusted futures
and empty-data handling; the documented monthly Treasury feed avoids its full
history download. yfinance history at `0c5a6c4939c2dba36b12a6d1a19c0366a7f2afb6`
(blob `af5f6d82b3044ab90e828e58e6d03bde69c05982`) provides the inspected chart/
timezone/error seam; no cookie/crumb recovery or package installation is copied.
CCXT at `11e215fe71d32870072ac22f92dad94aaba6de00`, coinbaseexchange.py blob
`b1bb98eca3ad1eadf11f0ef6406f6e9ac40034ea`: exact candle order, 300-bucket bound,
explicit product/start/end; no market-universe download, pagination or trade API.
No external implementation code or trading/provider framework is imported.
The current OpenBB Treasury path history was also checked: its last returned
change is `9f0d5928392ac7a3a127c0a8ca015e8d205bf33a` (2025-10-10); the inspected
current implementation still downloads the H15 full-history package. No new
dependency is justified merely to wrap that request for a 14-date background.

## Preservation and delivery boundary

Checkpoint precedes each HTTP. Preserve exact raw bytes, bounded safe metadata
(including Retry-After), request URL, requested/received times, run/code/attempt,
byte counts and SHA-256. Only exception types, never exception bodies, are used
for failures. Replay uses trusted installed code, strict source identities,
bounded XML without DTD/entities, dates, units, duplicate checks and original
bytes. Saved JSON/Markdown are checked against the independent replay.

A latest missing value is not forward-filled under a newer date. Retrieved XML
or candles outside the selected date window stay in the original bytes and are
counted but not projected. The window is a current retrieval of dated rows, not
an as-known historical vintage. Fetch time is not publication time. Market
sessions/open status, issuer exposure and economic causes are not inferred.

Artifacts retain for the existing 30 days. This slice has no new publisher
listener: verify real responses first, then adapt the existing #612 fixed-R and
Markets seam together. Do not call artifact retention permanent history or
source tests a production Site screenshot. One failure does not erase previous
artifacts or restart another family. No Quick/Full/Odds/Watch/trade is executed.

Exit: remove this caller/manual workflow and its dedicated tests together;
preserve original captures and any required historical reader once adopted.
No new provider router, cache, database, queue or recurring governance job.
