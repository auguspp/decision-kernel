# TDX post-upload custody correction — 2026-09-25

Authority: Human “那就做吧，东财退二线去” and “继续”; #364/#570.

The first main source run36096006542/attempt1 successfully captured and replayed
on its runner. The downloaded artifact10846812870 is nevertheless incomplete:
`source-files/.eltdx_board_cache.json` is named in capture.json but absent from
the eight-file ZIP. Existing exact-code replay rejects it with
`CAPTURE_FILES_REJECTED`. Offline inspection run36098577707/job107956002388
establishes this without another market request. The preceding archival attempt
36098445298 correctly stopped at its file-set assertion.

The official actions/upload-artifact implementation used by that run,
043fb46d1a93c77aae656e7c1c64a875d1fc6a0a/action.yml, defaults
`include-hidden-files` to false. The bounded fix explicitly includes hidden
metadata ONLY under the existing TDX output directory. It adds no source,
credential, schedule, retry, runtime/schema change or broader upload path.

Regression: actual synthetic capture -> ZIP -> fresh directory -> unchanged
replay succeeds with all files; the same replay rejects the hidden-file-omitted
archive. No source credentials or source network calls enter these tests.

Do not fabricate the missing old file, change its recorded hash, weaken the
reader or rewrite the old source failure as success. Source-call success,
pre-upload replay, complete retained bytes and normal-entry delivery are
separate proofs. A post-fix fresh source and downloaded-archive replay remain
required before final custody acceptance. Eastmoney stays secondary; HiThink
and existing historical artifacts remain unchanged.

Also retain the distinction: eltdx prepared_date is a preparation label derived
from handshake date fields/fallback local date, not an independently established
publication/effective date of the board-membership files. Daily bars establish
the price observation's date; historical membership PIT and same-day definition
updates remain NOT_ESTABLISHED. AI Investment Authority = NONE.
