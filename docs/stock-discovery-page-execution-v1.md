# Explicit Stock discovery page execution v1

Status: IMPLEMENTATION; fresh market execution and Human usefulness NOT YET VERIFIED.

Continues #297/5724678888 and #297/5725374688 under Human's approved Radar-r3.
Reuse Decision: REUSE + THIN_ADAPTER. Reuse #425's saved-result pool and page planner,
existing Stock context/price gate/capture/replay, existing native workflow inputs,
original saved-product publisher, and stable first-business Research identities.
No new engine, source, dependency, score, schedule, queue or automatic next page.
The earlier external GitHub native input/artifact review and EasyStock product
prior art remain the scoped reuse evidence; no EasyStock source code is copied.

## Actual change

`hithink-stock-dump-trial` retains the original `stock-reading` purpose and gets an
optional `stock-discovery-page` string: exactly `<pool_hash>:<offset>`. Empty input
keeps the prior daily/default route, versions and output unchanged. A nonempty
selection is retained in the invocation request and copied capture input. It
selects one bounded page from all original qualified groups AND granular drivers,
not just homepage groups. All origins, source bytes, clocks and names remain.

The adapter creates a distinct v9 Stock plan using the existing 16 issuer /
6 direction / 26 request limits and cost `4 + directions + 3 * issuers` (zero for
an empty page). It invokes the SAME `observe_stock_reading`, qualification,
5/20-day predicate, three-card presentation budget and original capture/replay.
The capture has a distinct version only for explicit pages. No caller-provided
stock list or arbitrary gate replacement is accepted. All current direction
states are preserved; an old entry in a now-inactive direction cannot establish
a current strong-path origin. The other origins may still qualify independently.

`discovery-dispositions.json` accounts for the entire exact source pool, while
`stock-reading.json` and its coverage account for this batch only. Prior-page
execution is NOT_ASSERTED; deferred companies are NOT_EXECUTED_BY_THIS_CAPTURE;
selected failure is not conditions-not-met. Each source snapshot has its own
pool hash. Offsets are not cross-day cursors, proof of earlier execution, retry
permission or automatic paging. Plans still do not establish investment priority.

## Source binding, failures and research

Replay reconstructs the page and full executable plan from original Sector/state/
company inputs and the retained selector, then replays the original recorded
requests. It verifies all JSON/HTML and full-pool dispositions without network.
The publisher explicitly recognizes the new route, binds invocation selector,
capture version, original Sector bytes, pool, origins, plan and dispositions.
Relabelling a page capture as a legacy route is rejected. This saved reader is
not another live price run or certification of provider truth.

The existing recent-26-session missing-bar reason now has a finite capture
explanation. A missing recent bar remains unavailable, not a made-up suspension,
zero-return bar, or conditions-not-met. No source qualification rule is relaxed.

The new pool can include BSE securities. They remain Stock observations, but the
existing first-business Research scope remains Shanghai/Shenzhen. New-page
Research intake explicitly retains unsupported rows rather than aborting every
supported company, and retained-work reading reports the same scope gap. It does
not expand CNINFO authority or produce a fake Research result. First-baseline
identity remains security + question kind; previous failures/roots are not reset.
The original Research permission, history, source preparation and admission are
still required. This implementation itself invokes no Pre, Quick, Odds or Action.

## Validation and remaining scope

Local new synthetic tests exercise actual original observation/capture/replay,
outside-homepage candidates, empty and noninitial pages, complete dispositions,
recent-bar isolation, transport failure, source/selector/origin/version tampering,
current-gate preservation, saved-product reader and unsupported Research scope.
All network calls are prohibited or explicitly injected synthetic envelopes.
The PUBLIC-code-path fixture is synthetic, not a real HiThink acceptance run.

The local source base is the complete 835-file native archive a659b4a, tree
06b8be8a3616fe137c0a57e5e53ddd17a0ba43bb. Canonical compare to current base a2197ec
confirms none of this slice's existing edited paths changed; the local environment
is nevertheless NOT the complete current-main checkout/pinned CI environment.
Some pre-existing tests could not collect locally because feedparser is absent;
no stubs/skips/dependency changes were used to conceal that. Full exact-head CI,
independent main CI and normal publication require their own actual receipts.

A fresh page must use a then-qualified latest completed Sector state and real
provider clock. The old 9/17 source is an offline historical planning sample, not
permission to request it during a later intraday session. No new dispatch has
occurred in this implementation. The current connector lacks fresh dispatch;
never substitute Re-run, GET, trigger edits or unrestricted auto-pagination.

Still open: real page execution/Research outcome, historical Stock-policy reader
compatibility, independent current concepts, continuous/no-new-event member
coverage, remaining Smart Money dimensions and daily discovery quality. This
slice does not close Radar-r3 or replace concept work with more Stock names.
