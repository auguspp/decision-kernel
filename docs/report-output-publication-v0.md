# Create-only report-pair publication

This bounded repair follows the reproduced C1 review findings in
[#297/5914712953](https://github.com/auguspp/decision-kernel/issues/297#issuecomment-5914712953).
The activity CLI previously created its final directory before writing JSON and
Markdown. A failed second write left a partial result and blocked same-path
retry. The comparison CLI used the same sequence and receives the same repair.
No archive format, report contents, provider, task or acceptance authority changes.

## One shared output primitive

`research_commit_only._publish_report_files` uses the existing safe-path,
bounded create-only write, file fsync and byte-readback primitives. Both CLIs
finish calculation and rendering before passing their two byte strings to it.

1. Validate the destination, existing parent, two plain names and bounded bytes
2. Create a private uniquely named staging directory beside the destination
3. Write and read back both files; require the exact expected inventory
4. Atomically rename the completed directory only if the destination is absent

Existing empty/nonempty directories, files and symlinks are never replaced.
A competing writer that creates the destination before publication wins that
name; this attempt fails without deleting or changing its result. A preflight
existence check alone is not the concurrency guarantee.

Linux uses the system `renameat2` primitive with `RENAME_NOREPLACE`, through
stdlib ctypes. Windows uses the documented no-replace behavior of `os.rename`.
Other hosts, missing primitives and unsupported filesystems fail closed rather
than falling back to POSIX check-then-rename, which can replace an empty target.
The actual regression execution platform is recorded with its test evidence;
documentation of another OS is not a claim of execution there.

## Failures and retry

A caught write, readback or pre-publication failure cleans this invocation's
private staging tree. The final destination remains absent, so the same output
path can be retried. A hard process kill may leave an orphaned private staging
directory; it does not reserve the final name. A retry uses fresh staging and
does not scan or remove other runs' directories.

After the rename, a complete output exists and is retained even if the process
is killed immediately afterward. An ordinary retry then refuses that existing
output; the caller inspects it rather than overwriting history. This is an
atomic local visibility contract, not a distributed transaction, hostile-parent
filesystem sandbox or guarantee against machine/filesystem power loss.

## Reuse and bounded acceptance

Internal staging patterns already exist in `economic_release_review` and
`economic_company_context`. Reuse their same-parent staging idea and the existing
report byte writer, adding the needed atomic no-replace terminal operation.
This repair does not broadly migrate unrelated publication paths.

Official contracts checked: [Python os.rename](https://docs.python.org/3/library/os.html#os.rename)
and [Linux rename/renameat2](https://man7.org/linux/man-pages/man2/rename.2.html).
The mature [atomicwrites](https://python-atomicwrites.readthedocs.io/en/latest/)
library offers single-file writes; its no-overwrite file-link approach is not
a two-file directory publication primitive. No dependency is installed or
copied merely to wrap the system rename. Decision: **REUSE + THIN_ADAPTER**.

Acceptance includes first/second-write and readback failure, competing targets,
real CLI retry, and subprocess interruption. Success preserves report objects,
hashes and rendered bytes. Local tests, exact-head CI, main checks, publication,
fixed-version recovery and webpage Pro review remain distinct stages.
