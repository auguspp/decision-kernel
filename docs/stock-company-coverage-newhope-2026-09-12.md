# P0 Stock business coverage — New Hope feed bridge — 2026-09-12

Status: bounded implementation/evidence change; **not a recommendation, Research route, Odds, Action or natural-schedule acceptance**.

The Human-authorized demo run `34658920384` successfully completed the Stock read/replay chain for market session 2026-09-11 but produced `BUSINESS_COVERAGE_INSUFFICIENT`, with zero planned issuers. The saved Sector artifact for that session shows `884278.TI 畜禽饲料` gate-active and its retained exact membership includes `000876.SZ 新希望`. This patch closes only that demonstrated gap.

Reuse first: `cn.livestock.price_feed` already retains national pig, corn and fattening-pig compound-feed observations, so no new economic node/provider/schema/selector is introduced. The reviewed link adds only `884278.TI`; it explicitly does not mean feed-index movement equals a company's selling price, cost or profit.

New Hope evidence is a limited extraction from the CNINFO-hosted 2025 annual report (`1225251161.PDF`). The company information binds 新希望 / 000876 / 深圳证券交易所; the business section states feed is a core business and describes premix, concentrate and compound feed across poultry, pig, aquatic and ruminant categories. Only business existence and customer/product boundaries are retained. Original PDF bytes are not stored in GitHub.

Production v3 inherits v2 unchanged and appends only New Hope. Old v1/v2 remain explicit replay scopes. Worst-case existing reservation is `4 + 4 directions + 3×6 issuers = 26`, exactly the existing limit; no second issuer, request ceiling increase or timeout change is included.

Evidence source commit: `11a6f20126633ca80bfff369a0a84732825e6f23`.

A future fresh Stock demo must still bind a qualified Sector state and pass shared-Key preflight. Success can still yield no surfaced stock if New Hope fails price/data conditions. Evidence changes Belief; Price changes Odds; this patch creates neither investment authority nor a buy recommendation.
