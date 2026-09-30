# Sector Radar Historical Outcome Study v0

- source state session: `2026-09-14`
- source state hash: `fe869bf419d4b4a75095578caf422d873082605635c84f490832358c2c6a8109`
- study hash: `bbe1500b75db1b73254fac2d074ba96a9de65e5ef9b69603eacc7bbf4afd62a6`
- formula: `sector-rs-5-20-60-persistence126-v0`
- Radar policy: `sector-shadow-state-entry-hierarchy-v0`
- baseline: `positive-20d-excess-top-decile-v0`
- universe qualification: `FROZEN_UNIVERSE_PRICE_PATH_ONLY__CATALOG_EFFECTIVE_DATE_NOT_INDEPENDENTLY_PROVEN`
- edge acceptance: `NOT_CERTIFIED__HISTORICAL_CATALOG_EFFECTIVE_DATE_UNKNOWN`

This is a frozen-universe discovery outcome study, **not** a trading backtest, Recommendation, Odds, Action, or Investment Authority.

## Cohort summary

| Family | Horizon | Radar n | Radar mean excess | Radar positive | Baseline n | Baseline mean excess | Baseline positive |
|---|---:|---:|---:|---:|---:|---:|---:|
| BROAD_881 | 5 | 120 | 0.63% | 51.67% | 545 | -0.25% | 46.61% |
| BROAD_881 | 20 | 66 | 2.68% | 71.21% | 410 | -3.10% | 54.39% |
| BROAD_881 | 60 | 4 | -4.31% | 25.00% | 53 | -7.43% | 15.09% |
| GRANULAR_884 | 5 | 344 | 0.33% | 52.62% | 1401 | -0.73% | 44.90% |
| GRANULAR_884 | 20 | 186 | -0.10% | 55.38% | 1056 | -4.68% | 45.45% |
| GRANULAR_884 | 60 | 17 | -8.43% | 17.65% | 138 | -9.15% | 16.67% |

False-positive / false-negative counts are forward-excess-sign proxies only; they are not investment-error labels.
Historical catalog effective-date identity is not independently proven in v0, so these statistics cannot certify historical production PIT truth or investment edge.
