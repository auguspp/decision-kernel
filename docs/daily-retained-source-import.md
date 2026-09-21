# Import saved source material into the existing daily Research path

Scope: #297 / 5762531470; follows #492 and Human's mainline instruction.
Reuse Decision: THIN_ADAPTER. No acquisition service, scheduler, new Research
executor, additional dependency or new company deep-dive.

The trusted exact-main `research_runs/stock-retained-source-imports.json`
explicitly binds a historical capture's original run identity, artifact identity
and all retained Git file identities. A daily custody record can opt into one
of these reviewed entries using `source_import`. Unlisted sources are rejected;
the original native source path is unchanged when that field is absent.

The importer checks the original workflow/branch/event/run, completed status,
artifact digest and inventory, exact raw files and original Git copies. It
re-expresses the saved inventory, PDF, extraction and acquisition receipt into
the existing daily reader's layout. Original capture clocks and the original
run are recorded as historical import provenance, never relabelled as a new
native capture. The entire report is reconstructed by the original PDF parser.
The imported journal is a deterministic interpretation, not an original wire
response, and must exactly match the separately retained journal reference.

The first reviewed entry is Zhenjiang's already retained CNINFO report. Its
FTShare-assisted acquisition and source commit were accepted in #491. This
profile is source-import configuration, not Research approval or proof of truth.
The existing daily policy still requires the complete batch review, question,
necessary body preflight, unconsumed question/day, original admission and
public-egress limits. Four PDFs / 32 MiB total, 448 KiB context, 512 KiB prompt,
6000 output tokens per stage, no retry/fallback/automatic Deep remain unchanged.

A fixed `daily-stock-question-ready` label on issue297 can transport the already
reviewed main request to the existing daily step. Repository, branch, sender,
event, attempt and code identity are checked independently. The label does not
authorize anything; a disabled/missing/unqualified main request cannot execute.
This reuses the original workflow and issue-trigger pattern, not a new scheduled
task. Existing Woton and legacy dispatch paths remain separate.

Reuse: original GitHubAPI/archive/unpack_archive, _retained_pdf, _saved_document,
PDF parser, preparation and host. Official cross-run artifact and Git interfaces:
https://docs.github.com/en/actions/tutorials/store-and-share-data and
https://docs.github.com/en/rest/actions/artifacts . Same-capability prior-art
reviews of native Git/PyGithub/pypdf in #491/#492 are retained; none supplies this
repository-specific identity/admission meaning, so no additional SDK is needed.

Acceptance separates synthetic native-host tests, actual retained-source replay,
actual current-main preparation, actual paid execution and natural Brief/Human
delivery. None is inferred from another. The source-import workbench is an
isolated development aid and is not included in this production change.
