# Sector Radar state bootstrap — 2026-09-04

Status: **DURABLE QUALIFIED INITIAL STATE / CONTIGUOUS DAILY APPEND REQUIRED / NO HISTORICAL MEMBERSHIP / NO HUMAN WAKE / NO INVESTMENT AUTHORITY**

## Frozen state

```text
latest completed session = 2026-09-04
rolling sessions = 127
window start = 2026-03-05
series = 321
benchmark = 000300.SH / 沪深300
broad industries = 90
granular industries = 230
catalog hash = 367d64660f5ef1f715ae0ef1d832a180d075ec7d6fc0a915797cbfafbd33f360
state hash = 2963d7fa62757a56e7296b3d9855a7d6d067d59816738078361f86c51d1f41d7
compressed SHA-256 = a398dd0ddf38ddd9ad080fa54c4c93b6f6c0f90d78f13ea5325fd144defcbccf
uncompressed SHA-256 = 2c2d659570db1de13552d4358ee3ea9560948bbc8b271c0755edc569cd45f920
```

Source lineage:

```text
broad / benchmark run = 33869436890
broad / benchmark artifact = 9936117543
broad / benchmark artifact digest = sha256:58de421f48f5d8d5ddafd1a702e1f676367f450da145948e932b186d6cd78816

granular run = 33878938737
granular artifact = 9941301222
granular artifact digest = sha256:4f716374797350a1160f45ae8468834b6e9bcee0932327ad9cbdebd4802c3671
granular result hash = 6dcef7ac20360491059405163c29114a8a3e2f6f07352c774dda81262b8af633
```

Every selected source checkpoint was re-hashed before state creation. The bootstrap is stored as deterministic gzip and round-tripped through the merged strict state parser.

## Use rule

```text
bootstrap only when no later qualified state exists
→ fetch exact current catalog
→ fetch one qualified complete index snapshot
→ require every provider prev_price to equal the cached latest close
→ append exactly one completed session
→ persist the new content-hashed state
```

A cache miss may restore this durable bootstrap only if the next completed market snapshot still proves direct continuity from 2026-09-04. Once the market has advanced beyond one session, this bootstrap cannot silently bridge the gap; recovery must use a separately qualified state rebuild.

The bootstrap carries no historical constituent membership, Research route, Human wake, Recommendation, Action, or investment authority.
