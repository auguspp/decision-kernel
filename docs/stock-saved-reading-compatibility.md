# Read the saved Stock v8 contract without replaying it as v9

2026-10-01; scope [#297/5935089201](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5935089201). Original C continuation; this fixes an observed reading regression, not a new acquisition or signal.

## Observed failure and cause

At M `cc13a34762314b6095567406a32c04344d7141bd`, ordinary reading R `5320a51f08fa359807255b5bfda2c208f0103729` rejected the latest successful Stock input with `stock reading identity or authority differs`. The original run `36702153468/1` at `ce22fa79ac841dea11d31541c86e4c4faeb1378b` saved `stock-market-expression-window-qualified-v8`. The action-reference changes advanced the producer to market-expression-v9, while the current-state reader routed only current versions to the market-expression validator. Old v8 therefore reached the wrong base validator. A green publisher correctly retained a labelled previous read copy; it did not prove the latest saved input was consumable.

The original ZIP remains artifact `11091190335`, 3,449,794 bytes, SHA256 `47f4ea4d31f4d575ebb5d16c64269aaaafc280d6ed5e07dc4cce35e6c333fec8`. Its projection hash is `53043e9edf25ed95d092b7c918bad29ae13a52e02b8672ab45a9d451fa1f7b47`, capture hash `2aa308ce96a5d020141b086f0b0d26379610bf85dc9afe1b3569d8d09477f446`. Reading this source must preserve six planned issuers, four qualified raw paths and two unavailable inputs, including business3002 and the raw price-reference discontinuity. It must not retrospectively apply #704/#705 to upgrade those failures.

## Minimal compatibility, not a new history executor

REUSE the existing version dispatch, canonical policy hash, renderer, capture inventory and saved Sector/state bindings. The old complete policy is pinned from the exact original code and report, rather than reconstructed from evolving current constants. This is a project-owned semantic compatibility fix: no new commodity capability, library, dependency, provider or serialization framework is needed. The original acquisition prior-art and qualification work in #704/#705 is unchanged.

Only the demonstrated market-expression-v8 reader is added. Current producer plans remain v9/v10 and still reject old v8. Unknown or modified policies fail closed even after resealing the outer JSON. Old v8 paths cannot acquire adjusted-price conventions, forward-fallback metadata or action-reference adjustments. The reader keeps both original market-expression dispatch points, including the exact Sector artifact binding; a discovery-page capture cannot be relabelled v8 to bypass its own contract. This change does not add support for arbitrary historical base or discovery-page versions.

The collector retains the original JSON, HTML, source ZIP and verification bytes. The renderer's historical notice is validation/display output, not a rewrite of source files. No latest source selection, expiry, identity, authority, partial-coverage, request budget, producer workflow, schedule, notification, Watch, Research or investment permission is relaxed.

## Verification and exit

A local function-slice check on the exact original ZIP reproduces the pre-change rejection and post-change acceptance with unchanged files, projection, capture and 4/2 dispositions. Seventeen synthetic regressions cover current/legacy reading, policy/version/authority/coverage/hash rejection, adjusted-price laundering, producer separation, retained inventory/run/Sector binding and discovery relabelling. The local check used inspected source functions with imports limited to the exercised seam and denied network/subprocess calls; it is not a full native checkout or independent source requalification. A missing local `CONTRACT` dependency was corrected in the temporary loader before testing; production code was not changed to satisfy that loader.

Formal exact-head CI, independent main, ordinary publication and actual new-R consumption are separate pending stages until their PR receipts exist. Publication acceptance must show that the same old source is freshly read, not that a new price observation or fifth usable issuer was acquired. The source's two genuine data gaps, C2 historical effective members/multi-period roles, original broker-model qualifications, Brief output and whole-C acceptance remain independent. Sites paused; D not started; Investment Authority NONE.


## Shared fingerprint follow-through

The first formal PR run `36890018980/1` exposed a dependency omitted by the local Stock-only check: Concept detail's complete implementation fingerprint includes `current_state.py`. Its original and single-Quick historical replay tests correctly rejected the new file hash. That failed run is retained, not rerun into success.

Review of the exact before/after module AST confirms that only `validate_stock` changed; all other functions and top-level declarations are unchanged. `concept_detail_capture.load_base` consumes the unchanged repository/clock/archive helpers, never `validate_stock`. All other sixteen implementation-map entries and the original Concept verifier stay unchanged. `POST_STOCK_READING_IMPLEMENTATION` therefore adds one explicit current map while retaining every old immutable map, including the now-historical delivery-continuity map. Both sides must still match complete reviewed maps before the existing private verifier binding is used. Tests update only the current-map expectation, preserve all old rejection checks and add one previous-delivery positive/strict-verifier case. There is no arbitrary hash acceptance, skipped replay, altered source receipt or module monkeypatch in production. Final diff is seven files; net new tests are eighteen.
