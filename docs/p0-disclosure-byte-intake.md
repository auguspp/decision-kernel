# P0-4B: exact saved packet intake, not another research engine

Approved roadmap: Issue #297. This is the unfinished byte-transfer part of #300, using its existing FIFO, reservation and archive validators. The next fixed request is CATL's September 8 packet, not a retry of the failed September 5 GigaDevice request. Native Scheduled remains deferred.

## Reuse and scope

`incremental_disclosure_intake` reads one explicit request at `research_runs/disclosure-intake-request.json`, the complete pinned work-tree inventory and its original packet bytes, and one saved successful scan archive. Auxiliary work records are inventoried, not claimed to have been semantically read. Missing/truncated/dangling history fails closed. The original `plan_one` chooses; `expected_key` only asserts that choice and cannot change its ranking.

The existing GitHub read client handles bounded GETs and raw ZIP retrieval. The GitHub CLI performs at most two native Contents create-only PUTs on `research-work/disclosures-v0`: exact `packet.json` bytes, then `intake-plan.json`. Base64 encoding is mechanical, not model transcription. No old SHA is supplied, and no shell evaluates source data. The original client's write guard is unchanged. This is a fixed-path operational capability, not a global permission sandbox.

The saved source archive and selection plan, actual GitHub metadata, exact output bytes and phase receipt are retained as an Actions artifact. A successful receipt means the packet and plan were committed and read back byte-identically. It does NOT mean source readability, admission, completed Research, a Funnel result or registration. Original #288/#291 and the unchanged research receipt remain required afterwards.

## One explicit request, no automatic retry

The thin workflow listens to successful attempt-1 main push CI and checks whether the request file changed against that commit's first parent. Unrelated later CI is not an execution trigger. It checks out the tested commit, checks current main and expected work tip before the write, and rejects expiry. The workflow serializes its own intake jobs; this does not lock all accounts/branches.

An already retained expected packet is returned as `ALREADY_RESERVED_NO_EXECUTION`, without downloading another archive or selecting a replacement. Any write error or uncertain response stops, preserving the receipt. Read back the native work ref before deciding anything further; do not Re-run, delete/reset a reservation, change the key to escape failure, or interpret no output as permission to launch Research. A new request requires a deliberate authorized update, not an automated timeout reset.

The initial request is bound to saved scan34354228621/artifact10105040865, work commit c355eea159a1113704b06d19942fe277f56591e2 and original packet hash. It neither re-fetches issuer PDFs nor certifies that scan as today's production. The existing natural scan remains responsible for subsequent raw-body capture under #302; no extra scan is started for this intake.

## Acceptance

Synthetic tests exercise the real original packet/archive/FIFO functions and simulated native GitHub responses, including Unicode preservation, stale/malformed inventory, changed FIFO, identity failures, lost write responses and failed readback. They do not prove a real remote reservation. Exact-head repository CI, the ensuing real main-CI event, actual intake artifact and remote byte readback must be checked separately.

After exact intake, perform bounded source preflight for the actual selected question, then freeze the original input/budget before actual Pre/necessary Quick. Keep the old GigaDevice failure and #296 limitations unchanged. Engineering continuation is not a Human company-research response; no investment or automatic Deep authority is added.

CLI reference: https://cli.github.com/manual/gh_api (`--input -`, explicit PUT). GitHub Contents reference: https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents . Standard GitHub Actions checkout/setup-python/upload-artifact are reused; no dependency, scheduler, provider, agent or Gate framework is added.
