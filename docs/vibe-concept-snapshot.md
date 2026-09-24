# Vibe concept snapshot — R5-4 bounded source reuse

Authority: #297 comment5811035673 and #364 comment5811149133. Human asked this
conversation to take over Main Construction and continue with the Vibe reuse
route. Baseline main a0c22a9046945f2d9f2fc1dfefb1b2f3adb08e35; inspected reading
93b91e614a88b1c916ef047c8904c9d68f51495b. This is not #364/P1 completion.

## Reuse decision and exact scope

Reuse Decision: REUSE + THIN_ADAPTER. Upstream is
simonlin1212/Vibe-Research@7f3a08b85451b54c762898789e2dcaa5d7d2ec98:
`.agents/skills/data-access/scripts/sources/eastmoney.py::board_fund_flow`
and `.agents/skills/data-access/scripts/tests/test_eastmoney.py` (pagination
regression blob3a84126e237fc681deece74306de78492fc2cc63). Reuse its concept query,
today/5d/10d field mapping, actual-page-size lesson and current `EM_PUSH2_HOSTS`
ordering (`push2delay.eastmoney.com` before `push2.eastmoney.com`). The 496/100 regression
was an industry sample/test, NOT today's number of concepts. A catalogue entry
or unit test is not proof of live availability or field semantics.

Internal reuse: existing easy_stock_context JSON/Decimal/clock/seal and authority
helpers; hithink_dump_trial isolated Requests session and response checks;
sector_radar_audit safe-JSON checks; native Git, exact-head CI and Actions
artifacts. The existing EasyStock module keeps its own PolyForm Noncommercial
notice unchanged. No upstream application, data lake, scheduler, provider
framework, score, candidate-selection engine or research method is imported.
Official ecosystem reuse follows the existing reviewed Requests/GitHub
checkout/setup-python/upload-artifact and manual input patterns; source requests
use fixed reviewed parameters, not source-supplied destinations or commands.

## What this source does, and does not, answer

It requests Eastmoney `m:90+t:3` with BK identifiers, separately for today, 5d and
10d. Each returned page is kept with its exact request, clocks, byte length and
hash. Rows are requested by source code rather than gain/flow ranking; actual
unique rows must match a stable provider-reported total before that window is
marked `matched_reported_catalog`. Short pages do not certify completion.
Empty pages, changing totals, duplicate codes and invalid identity preserve
prior acquired pages but leave coverage incomplete. Missing numbers remain
UNKNOWN with field gaps, not zero. All acquired codes survive in JSON/Markdown.

A matched reported total is not an independently complete market universe or an
atomic snapshot. Different windows retain their own names, membership and raw
row locations. The source does not establish a trade date; current retrieval
time does not certify source freshness or historical availability. Rolling
5/10-day returns are NOT daily persistence and do not replace full 5/20/60-day
OHLC. The old TI catalogue and its 390 denominator, #541 and FTShare BK histories
are unchanged. No f24-to-20-day assumption is introduced. Field meaning is the
pinned Vibe mapping, not independent economic verification. Source-defined flow
is not company cash flow or proof of business benefit.

## One bounded manual execution; existing production is unchanged

`.github/workflows/vibe-concept-snapshot.yml` is manual-only on exact main,
attempt1, with a matching explicit code-sha input and a successful independent
main CI required BEFORE source access. It has no schedule/workflow_run trigger,
provider secrets, model call or write permission. Its own workflow/artifact
identity prevents a new BK format or skipped source job from poisoning the
old Concept/Industry readers' latest-run selection. No existing workflow changes.

The whole attempt permits at most32 requests, a180-second next-request start
budget,1MiB per HTTP response and4096 reported rows per window. Fresh isolated
sessions carry no environment/netrc credentials or redirects. Version v2 fixes
this bounded adapter to Vibe's current first push2 host `push2delay.eastmoney.com`;
it does not implement an in-run host cascade or automatic retry. HTTP/transport/
contract failure still stops this provider and cannot be hidden by another window. A retained failure can have a successful workflow
receipt while observation status remains PARTIAL_OR_UNAVAILABLE. A hard timeout
without sealed observation is an execution failure, not empty market activity.

The source writes plan/capture, original pages, derived observation and summary.
The CLI replay re-derives from retained raw bytes under expected execution
identity, makes zero source requests and checks any supplied derived files byte
for byte. Workflow metadata/CI admission and source economic truth are separate
checks; a matching hash alone does not authenticate an external fact.

## Acceptance and next consumer

Development focused tests cover the upstream pagination failure case, negative
tail, unknown values, source failure, global budgets, execution/custody mismatch,
replay and safe display. Full exact-head PR CI, independent main CI and ordinary
code publication require actual receipts, not this document. No old test or
source/replay fingerprint is changed by this slice.

The first live v1 trial `35983118410/attempt1` retained its real failure: the
then-fixed `push2.eastmoney.com` today/page1 request returned HTTP 502, so zero
rows were qualified and WHY remained UNKNOWN. That evidence motivated v2's
minimal host correction rather than a retry framework. The next fresh v2 trial
must retain its own result or failure and run/artifact identity. Ordinary GitHub retention/index discoverability and repeated daily
operation are separate follow-ups through existing mechanisms. This file does
NOT activate a normal current-state source consumer, establish live full
coverage, close all-batch continuity or claim research usefulness. Broad snapshot
readings supplement Hosted Quick; longer histories remain available as separate
work when needed. No automatic Quick, Full, Odds, Watch, alert or trading.

## Upstream MIT notice

Copyright (c) 2026 simonlin1212

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
