# Concept detail: bounded historical replay compatibility

Engineering scope: #479; no source acquisition, model call, producer rerun,
workflow change, authority expansion, budget increase or original-data rewrite.
Reuse Decision: **THIN_ADAPTER**. This is one reviewed equivalence pair, not a
historical-code loader or a general version-compatibility promise.

## Regression and admissible pair

PR #478 changed root-index JSON formatting in `current_state.py` and the root
emitter in `current_state_delivery.py`. The entire two files participate in
`concept_detail_capture._implementation()`, although the changed operations are
not used by detail replay. The other fifteen fingerprinted files, the detail
capture verifier and the primary verifier are byte-identical. The old capture
therefore remains valid under its original code but fails the current strict
identity equality. This is an implementation compatibility regression, not a
remote-source outage, data deletion, or economic conclusion.

`concept_detail_compat.py` requires equality of BOTH complete 17-file mappings:
the original mapping retained by run 35355234987 and the installed mapping at
main d61edb280d544daff9b5df5a3053c01c6bd1a675. Missing, extra and changed entries
on either side reject historical compatibility. The complete mappings are
immutable constants, not values inferred from an artifact version label.

Current captures still call the unchanged `concept_detail_capture.verify`.
For the reviewed historical pair, Python's existing `types.FunctionType` binds
that installed verifier's code object to a private copy of its globals, replacing
only the invocation-local `_implementation` expectation AFTER both mappings
have passed. All inventory, hash, source, base ZIP, plan, timestamp, request,
authority and byte-for-byte result reconstruction checks remain in the original
function. No global monkeypatch is made; concurrent current and historical
replays cannot change each other's expectation. No saved receipt is rewritten
or rehashed. The returned verification must still exactly equal the original
`verification.json`; the read status separately records `replay_mode` as
`CURRENT_IMPLEMENTATION` or `REVIEWED_HISTORICAL_EQUIVALENCE_478`.

A future change to any tracked installed replay file requires a new explicit
equivalence review or an exact historical replay mechanism. Do not automatically
refresh these constants, omit shared files, accept a semantic-version label,
ignore the identity guard, or convert a mismatch into success. This adapter
makes no claim that untracked dependencies are newly fingerprinted; it preserves
the existing capture implementation contract. Outer Collector run/artifact/
primary-binding/expiry checks remain mandatory and unchanged.

## Reuse evidence

The existing #479 start receipt records the internal verifier/Collector/Stock
and Sector replay review, official Git/Python capabilities, and inspected
asv fixed-revision checkout/test prior art. Reuse that exact review rather than
installing a benchmark framework or creating another replay service.
This implementation additionally uses the standard Python function-object
constructor and immutable mapping wrapper, with no added dependency:
- https://docs.python.org/3.12/library/types.html#types.FunctionType
- https://docs.python.org/3.12/c-api/function.html#c.PyFunction_New

The constructor receives only trusted installed code; artifact TARs remain inert
in production. The independent historical-code control below was executed only
after the complete archive source tree matched a directly retrieved Git tree.

## Actual local control and real-source proof

Artifact: 10551194627 from run 35355234987, 6,297,189 bytes, SHA256
`edb758fa3314213bd950906a573b1819ed7d90a0742479d0c0f67f57bad20436`.
Actual downloaded ZIP CRC and all 16 listed payload-file digests passed.
The 17 payload files including the capture receipt were unchanged after replay.

The archive's complete source tree was independently reconstructed as
`efa58ceb597b1f130accff143740e4b273505035`, matching GitHub's tree for original
commit `8abe024ff10a76b638ca1cf467d58f09906a0398` before source execution.
Original-code replay rebuilt the exact saved verification with networking
blocked and zero attempted network calls. Applying only #478's two relevant
changes reproduced `DETAIL_CAPTURE_IDENTITY_REJECTED`. Their reconstructed
Git blobs matched current main: `6672e1d44540b59c07904f903af0708858b528da`
and `166c4203d609c669684d68326ec823fa69d949a0`. GitHub's exact-commit comparison
confirmed that the other fifteen tracked implementation files were unchanged.

The compatibility path then rebuilt the exact ORIGINAL_CONCEPT_DETAIL_REQUESTS_AND_RESULTS_REBUILT
verification, still with networking blocked and zero attempted calls:
- capture hash: `e31b9ead4702d078b4bd62beb0c199ff60308d3c779d58b228bafa6b52854e3d`;
- projection hash: `0bec7f56ca60300377a70a9036673bdc83ac7ed5da5093b0ccad49132769d7ab`;
- 3 historical details and memberships, 0 detail gaps; 708 new-member union,
  698 outside the original details; not full-market or fresh coverage.

Local focused execution: 107 passed in 10.13s across the new compatibility tests
and unchanged supplement/preflight tests (Python 3.13.5, pydantic 2.13.4,
pytest 9.0.2). This used a verified historical checkout plus the exact current
tracked replay files, NOT a full current-main checkout or the production CI
environment. Two additional Collector integration cases belong to full PR CI.
The original full suite is unchanged; do not substitute these local tests for it.

## Release acceptance remains separate

Require exact-head PR review and full CI, independent main CI, normal publisher,
and a newly pinned read-model readback showing the SAME original artifact as
VERIFIED_SAVED_CONCEPT_DETAIL with the explicit historical replay mode. Verify
that the compact root is still at most 192 KiB and Woton financial r2 remains
available. Keep source failures and archived history intact. A successful
workflow alone does not establish these results. Review by the implementing
model is a same-model review, not independent Human or economic acceptance.


## R4-1 / PR #530：研究交接展示的追加兼容

单Quick接线只改`current_state.project_handoffs`中的两处对象投影：
`parsed.research_funnel`改为共享无权限wrapper，哈希材料改用`parsed.identity_material`。
旧v1的identity_material仍是原Funnel完整model_dump；新v2不伪造Funnel。
该函数不在concept detail的capture/plan/replay路径内。当前17项捕获指纹中，
相对PR529只有`runtime/current_state.py`从`e31f54cd...`变为`1faa6925...`；
其余16文件相同。完整哈希保存在原compat模块，不用前缀比较。

原HISTORICAL_IMPLEMENTATION完整保留，原REPLAY快照保留为
PRE_SINGLE_QUICK_IMPLEMENTATION；只有这两个精确旧映射在新精确安装映射下
允许复用原校验器。不是忽略current_state文件、任意版本白名单或动态接受当前代码。
来源原件、capture_hash、请求/计划/clock/结果重建、错误传播和不改receipt全部保持。
旧#478与PR529来源分别标记原模式及REVIEWED_HISTORICAL_EQUIVALENCE_530；
直接原capture.verify仍严格拒绝旧实现，新增回归覆盖这一区分及旧handoff哈希不变。

这只是本次必要的历史读取兼容；不是新的概念取数、扩大覆盖或方法有效性认证。


## 2026-09-25 — #579 Sector backfill fingerprint transition

PR #579 changes two modules that are inherited into the broad concept-detail implementation fingerprint:
`runtime/hithink_sector_breadth_http.py` and `runtime/sector_radar_audit.py`.
The change adds an explicit exchange-closure qualification path for a bounded
Sector/Stock backfill and records/replays that optional Sector audit input.

Concept-detail capture/replay does not call the all-market Sector stock-reference
path or the Sector audit producer. Its source requests, base Concept payload,
inventory, clocks, hashes, request ordering, report rebuild and authority checks
remain unchanged. Therefore the old retained concept-detail receipts remain
eligible only through the existing reviewed historical maps; their bytes and
historical implementation fingerprints are not rewritten.

`POST_SECTOR_BACKFILL_IMPLEMENTATION` is a new installed-side fingerprint map.
It equals the previously reviewed `REPLAY_IMPLEMENTATION` except for those two
Sector-only file hashes. The compatibility verifier still requires an exact known
historical receipt map and an exact reviewed installed map before it privately
binds the historical fingerprint for that one verification invocation. It does not
mutate the module, receipt, archive, Research state, or source evidence.
