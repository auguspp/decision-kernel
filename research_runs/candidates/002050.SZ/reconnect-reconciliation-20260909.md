# Reconnect readback reconciliation — 2026-09-09

Scope: continuation provenance only. Not Research, admission, semantic acceptance or promotion.

After Human reported reconnecting GitHub, the main read returned `381f4d1f826a6d98844d27d626129211218ca332`.
The candidate branch `research-candidate/p0-4a-sanhua-20260909-6d91` now resolves to `05c67a2636d10e445f5ee533549792f464cb3ebe`, not the previously reported `44fd8b6c958badeceed2009ffa731dc1a658ff58`.

The exact remote compare shows two intervening commits:
- `3ea47d903df9055c0cbffca4b95b69961e75710e`: preserved interrupted original attempt, Git commit time 2026-09-09T09:42:50Z.
- `05c67a2636d10e445f5ee533549792f464cb3ebe`: added separately identified input `p0-4a-sanhua-20260909T094013Z-cc72`, Git commit time 2026-09-09T09:43:26Z, input blob `50eb2bce246f9572ae53692c923dab45b1255b50`.

Therefore the earlier blanket statement that no later candidate write existed is no longer supported by remote readback. The prior Resource-not-found tool responses remain observed errors; they do not establish that all intended effects were absent. This review does not infer when or why tool visibility changed, or attribute the commits to an unobserved execution path.

The local continuation-ready.zip contains a DIFFERENT provisional identifier `p0-4a-sanhua-20260909-r2-e5b7`. It must not overwrite, substitute for, or be conflated with the committed cc72 input. No additional Research attempt is authorized merely by this reconciliation.

Next: inspect the exact committed input and any admission/execution records; preserve existing bytes, verify validity and original-model binding, and continue only under the existing admission and execution rules. No new source request, workflow trigger, registry/Human change or main update is part of this file write.

The write response and exact-commit file readback must be checked separately; this document itself does not certify write success.
