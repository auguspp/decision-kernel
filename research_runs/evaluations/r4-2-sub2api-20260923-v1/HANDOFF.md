# R4-2 current handoff: permission retry completed; review found a host-to-model source-status gap

**Current: the fixed two-material pilot has completed. No longer waiting for Sub2API permissions or a monetary budget.** Human's explicit retry permission is #526/5797702255. The original403 and original launch/request/usage remain unchanged. The preceding handoff is preserved at commit a3785f7264771836c8abff87e82b20834c4563b7 under this same path; it describes the historical stop, not the current inference status.

Actual retry run35883542962/attempt1, codee8b06ae6a7a4df5201eb501c28130ff7a1692fda, workflow25fbf3b8fd523a0e8da8e2af4b6d7403a5f64372. All7 new requests returned completed model output and usage; same Sub2API/requested and returnedgpt-6-astra, no auto retry/fallback. Original403(1)+new7=8 lifetime requests, below the authorized9 maximum. Jiangxi O Pre stopped, so its Quick was not called. No fill-to-quota request.

Raw result commitf87033f58669c49f370025c6e3b9dd17991c5b18 retains53 files under continuations/permission-retry-1/. Independent native Git reconstruction of those exact artifact files matches remote subtree009c69253bf72c541c903d00bc21f7fe5aa354c7. Artifact10762313238 has57 files/1814124bytes/SHA256a76c289364c2e51bfea4ce180cdda121a7c9a21fefd28e286598720212e2df80; publication.json and3 diagnostics are artifact-only sidecars.

Read [the content and A/B review](continuations/permission-retry-1/QUALITY-REVIEW.md), [actual token/accounting checks](continuations/permission-retry-1/metrics.json), and [retention proof](continuations/permission-retry-1/retention-audit.json). Raw outputs/requests/receipts at that child are not modified by this review.

## Interpretation, not automatic acceptance

600362: O Pre STOP, S0 STOP, S1 FULL_CANDIDATE with a source-check caveat. 603507: O Pre continues then Quick STOP; S0/S1 STOP. Single Quick preserved the checked financial distinctions while reducing repeated input in the one usable two-call comparison. Both methods and policies now correctly compute the Zhenjiang85.6% profit-increment proportion; that improvement over old DeepSeek outputs is not attributable solely to single Quick.

A real common-mode limitation remains: the stored Jiangxi preflight and admission record the correction-inventory check, but the model prompt passes its required-class declaration without the bound result/window. O/S0 use unseen host status as a STOP reason; S1 still carries the missing-status caveat. Do not interpret O/S0 as a business rejection, or S1 as an accepted/authorized production Full candidate. Preserve each raw route; do not edit answers to make the pilot green.

**Next approved engineering seam: a thin host-to-model handoff of already-validated source-check facts, clock/window and exact references.** Keep real source admission/identity/consumption checks and separate technical gaps from business dispositions. No second Pre, new permanent gate, recovery platform, source refresh or automatic retry. This fix is identified, not yet implemented/submitted. It does not reopen the completed R4-1 migration.

R4-2 real natural observation -> unconsumed question -> Quick -> normal Brief/Human feedback is still unaccepted. R4-2.5 Hosted Full is NOT_RUN. This is a two-case, unblinded same-model review with source-text spot checks, not independent Human/PDF/full-company validation. Model weights and actual account bill remain unknown. No daily production, Full/Odds, Dashboard or P2 was activated. #531 remains a non-production draft; #525 stays parked. Main and original research-work were not written by this experiment.
