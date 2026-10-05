# D / #331: saved benchmark structure in the normal reading

Scope: the current #509 engineering delivery, following Human's instruction to
finish usable D features rather than stop at each archive seam. The method stays
shadow / human-readable context. This is not policy, trading or full D acceptance.

## Reuse and ownership

Reuse Decision: **REUSE + THIN_ADAPTER**. CZSC 1.0.1 owns fractals, strokes, centres,
unfinished structure and their current finished membership. The reviewed source is
`90372af035f01ed9f05070eadddd265b91c84d24`, with explicit `max_bi_num=50` and
`min_bi_len=6`; use `from czsc import CZSC, RawBar, Freq`. No copied Chan algorithm,
trader, generic state service, pickle restore, new provider or chart engine.

The exact upstream inspection and real 160-bar shadow evidence are retained in
[#509/5980091863](https://github.com/auguspp/decision-kernel/issues/509#issuecomment-5980091863).
The original five-file readable selection is at commit
`019aa648eb7fcc9cefcfe2e41853bae28848c594`, directory
`docs/readings/d331-czsc-retained-2026-10-04`. Its new NAVIGATION_ONLY on-demand
registration does not copy the full shadow evidence or upgrade it to Research.
Original snapshots/logs and the corrections to older incomplete reports retain
their existing references. Registry visibility, publication and actual recovery
must be checked after delivery, not inferred from this document.

## One existing acquisition and publication chain

The existing Sector `fetch_snapshot` already obtains completed benchmark history.
This consumer uses the original saved audit/manifest, original archive byte and
expiry validator, and original HiThink calendar/history adapters. The benchmark
identity, request paths, response locations, dates and window are read from that
capture; no fixed September endpoint or hard-coded 160-bar requirement. It then
preserves original OHLC/volume/amount decimal strings and normalizes only this
index geometry purpose. Stock interval comparison remains a different use.

When a later Sector operation fails after valid benchmark capture, those complete
saved inputs may still be used; the failed attempt and lane gaps remain visible.
When history itself is missing, invalid or stale at capture, the consumer cannot
invent it. This does not establish independent acquisition during every Sector
failure: it only reuses inputs actually present in an admitted archive.

The original publisher runs the optional engine in a normal child process with
no inherited credentials, no data client and a 45-second limit. Python network
audit events are denied before engine import; this is not an OS sandbox. The
worker admits at most 512 bars and 512 KiB JSON input/output for resource safety,
not as another purpose's admission condition. A one-bar input is valid; there is
no minimum 61/160-bar gate. The unchanged upstream algorithm determines whether
structure is present. Missing long history is not filled or interpreted as quiet.

Results use `details/stock/price-structure.json` and
`details/stock/price-structure-input.json`; the first is indexed in the original
`current-state.json` research navigation, and README shows every retained stroke,
centre and observation date. They are index context, not company Evidence. The
existing read-model commit history preserves each published version. No new
scheduler, acquisition call, archive service or automatic Research routing.

## Time, changes and honest limits

`source_captured_at`, `computed_at`, selected `market_session`, window start,
source attempt, previous reading commit and actual first observed stroke times
remain distinct. Prefix visibility/finished/withdrawal dates mean only “the
retrospective pass has consumed through this bar”. They are not historical public
availability timestamps. Daily datetime is a market-date label, not midnight
knowledge. No final-state label is backfilled into a previously published file.

The optional stage closes the root through the existing `current_state.assemble`
after computation (or a recorded failure), rather than inheriting the earlier
base stage's completed check. Root `generated_at` / `checks.finished_at` and the
structure's `checked_at` share that completed-stage clock; the original check
start, source capture, market dates, native `computed_at` and old Git readings
are not backfilled. Same-input reuse advances the check, not the computation or
first-observed clock. A future worker clock or reversed collector clock cannot
publish a current structure. README's structure section states this stage's
cutoff explicitly; earlier sections retain their own prior-stage context.

Each pass retains prefix input/native/state hashes, counts, current public geometry
and the complete stroke event/lifecycle list for that window. Full per-prefix
geometry and FX/centre lifecycle diagnostics remain in the prior shadow study;
this normal reading does not claim to replicate its complete 480-snapshot package.
Source Decimal strings and actual native float `repr`/`hex` are bound separately;
float values never replace original source strings or canonical Kernel inputs.
The unchanged `d_market_expression.close_structure` supplies the close baseline.

Repeated exact admitted source bytes reuse the saved result without native
recomputation. Unchanged price history is not a new market event even if retrieved
again. Source revisions, changed method/subject, non-advancing endpoints and
rolling lookback changes are classified separately. Only an exact prefix append
reports pure forward structural additions/removals; lookback shifts do not become
claimed signal invalidations. First observed timestamps remain for matching
geometry. Reappearance after absence is a new observed episode; older episodes
remain in previous Git readings rather than a second ledger.

`finished_bis` is explicitly revocable: the retained study observed 12 tail
withdrawals including three previously finished strokes. Capacity eviction is
separate. Different lookbacks may change centres. These observations are not
rewritten as “permanent confirmation”, “no repaint”, or algorithmic truth.

## Optional dependency and failure isolation

Only generating environments need `.[price-structure]`; readers of saved JSON do
not. Fixed runtime wheels already used in the shadow form the optional extra.
The full dev suite includes the real engine so it cannot silently skip the new
native tests. Base Kernel dependencies are unchanged.

The existing publisher attempts the optional prebuilt dependency install after
its original installation. If that optional install fails, the step explicitly
records failure in the job summary; base reading still runs and the structure
consumer records its own unavailable result. This is not a successful native
validation. The normal full PR CI contract is not relaxed or made optional.

Source/worker/timeout/size/quota errors roll back only this addition. Existing
prices, Research, Human decisions and lane failures remain byte-preserved. A
previous exact reading locator is retained when available, explicitly not current
success. Existing shared API/blob reservation and total/root/detail limits apply;
no limit is raised, no unlimited fallback or market request is added. Installation
or source failure must not be presented as zero opportunities.

## Delivery validation

Use the original PR full CI, exact-head review, independent main validation,
normal publisher and fixed-R readback. Check root descriptor/input/report hashes,
all rows in README, latest failure visibility, unchanged research/decisions, and
second-reading unchanged-source reuse. Local partial-source tests are not full CI.
The fixed saved 160-bar source is a regression, not today's market or a natural
run. The normal source chain must separately demonstrate future-session updates.

Remaining D obligations include true intraday input/leadership, auction timing
and T+1, company-economic transmission and multi-horizon cases, natural consumption,
and point-in-time/out-of-sample incremental value. None is signed by this feature.
Investment Authority = NONE; C and D remain IN_PROGRESS.

## 2026-10-05: keep the explicit predecessor across unavailable readings

A real publication sequence exposed a continuity defect, not a missing CZSC rule.
R `440c03166d89debe08d3bb4a0b5e104c923009b2` retained a 160-bar, 15-stroke
report (14 strokes then in `finished_bis`). First failed R
`9176d5dfb098984e8fa69bfcb8efb479cd167c63` kept that exact report locator;
next failed R `9eb3dc3e950b9a3f61b682791e1b7624d9f50178` discarded it because
`_previous` read only direct descriptors. Its actual source artifact
`11338901084`, SHA256 `ffee680bffd4824b391382bec31e8231fcdfb6d78c4c9f8cc7cec2e013e0e3ae`,
contains only `operations.json` and `operations.md`, not benchmark geometry.
The source failure remains real. Do not substitute an older successful archive.

The correction follows at most one explicit `previous_saved_reading` locator.
Commit/path/descriptor, bytes/blob/SHA256, report hash, market date and report
clocks are checked using the original Git reader and shared reserve. Repeated
failures carry the same locator and display its immutable history link; a file
read failure is recorded separately and does not erase the recorded location.
No parent walk, history search, retry, native reinstallation or budget increase.
Malformed locators make no Git request and cannot block valid current inputs.
An already-lost locator is not invented or retroactively repaired by this code.

If a later independently eligible current input is identical, reuse retains the
original computation and first-observed clocks. A recovered predecessor points
to its real successful R, not the intervening failure R. The current reading
explicitly marks the interruption: comparison of observed endpoints does not
prove continuous visibility, absence of withdrawal, or absence of reappearance
inside the gap. Changed sources/methods still follow the original comparison.
This is no new probability, signal rule, Research, Human acceptance or trade.

Reuse: KEEP the exact CZSC 1.0.1/50/6 audit and algorithm above; THIN_ADAPTER of
the already-owned explicit Git predecessor/failure contract. No new generic
capability or dependency is selected, so that exact upstream review remains
applicable. Source selection, company/horizon/Human records and #749/#750 files
are unchanged. Remove this resolver and its focused tests to revert the fix;
all original reports and failures remain immutable.

Local evidence: original code reproduced the second real R's missing locator;
the corrected reader retained it across two offline failed passes using the
original 1,364-byte failure ZIP and bound historical report. Collector Git I/O
and quota are local substitutes, not a full publisher. Fifteen new synthetic
continuity cases and 17 existing source-normalization cases passed; two decisive
new regressions fail on the original code. CZSC is not installed locally, and no
native-engine result or complete CI is claimed. The 2.3 MB successful source ZIP
was not retrieved (`get_file_contents`: unsupported encoding `none`); normalized
input/report identities were checked, not full original source re-normalization.
Formal exact-head full CI, independent main, publication and fixed-R readback
remain separate. This fixes reading continuity, not the upstream Sector cache
conflict or the D economic/predictive goal. The historical report remains directly
readable at [its original R](https://github.com/auguspp/decision-kernel/blob/440c03166d89debe08d3bb4a0b5e104c923009b2/details/stock/price-structure.json).
