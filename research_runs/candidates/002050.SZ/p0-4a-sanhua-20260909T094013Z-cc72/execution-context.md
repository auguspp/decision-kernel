# cc72 execution context and provenance limitation

The exact original input remains `05c67a2636d10e445f5ee533549792f464cb3ebe`, blob `50eb2bce246f9572ae53692c923dab45b1255b50`. This is continuation of that committed execution, not a third identifier or a modification of its cutoff/budget.

On 2026-09-09 the main conversation installed the unchanged source package archived in saved Actions artifact `10095294054` (code commit `381f4d1f826a6d98844d27d626129211218ca332`). Actual original `execute_after_admission()` returned `RESEARCH_EXECUTION_ALLOWED`, finishing its check at `2026-09-09T10:17:49.033728+00:00`. The two mutable-main callbacks were fulfilled by new GitHub connector reads while the original gate was suspended, both returning the pinned main. Pinned file responses were serialized locally and accepted only after matching their original Git blobs / SHA256; canonical input hash is the original parsed-model hash, not raw JSON hash. The callback then read/extracted the six saved original PDFs and printed `SOURCE_READS_COMPLETED 6`.

At the next filesystem read, the new local work directory and the just-created action journal were absent. A subsequent listing showed the mounted attachments again but not that work directory. This is an observed local-workspace continuity failure; its cause is UNKNOWN. It does not establish any GitHub or CNINFO failure.

The actual gate JSON survived in the tool response and is retained separately as `admission.json`. Its `status=NOT_EXECUTED` describes the check itself, as documented by #291; it is not a statement that its executor callback was never invoked.

The early six-read journal bytes / individual timestamps did NOT survive. They will not be reconstructed and presented as original telemetry. The six reads remain charged to the same 32-action / 24-read budget. Subsequent direct re-reads for analysis remain inside that budget and the same 45-minute execution interval. For conservative elapsed accounting the gate finish is the lower bound of executor start, so the deadline is no later than `2026-09-09T11:02:49.033728+00:00`. No budget reset, new source request or new Research attempt follows from this note.

Execution-process provenance is therefore PARTIAL / EARLY_JOURNAL_NOT_RETAINED, regardless of whether source analysis and deterministic Funnel validation later complete. A finished Research candidate must not be claimed to provide complete original-process certification. Subsequent action summaries must disclose their actual recording times, retained-source identities and whether they are summaries rather than platform-native telemetry.

No Human decision, investment authority, registry registration or main change is made here.
