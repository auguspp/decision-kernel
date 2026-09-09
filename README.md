# Incremental disclosure work records v0

Requirements: auguspp/decision-kernel Issue297; implementation PR300.

This fixed data-only work ref retains exact saved DisclosureAssessmentPacket bytes and subsequent attempts. It is not a production Research registry, Human decision store, market state, or restore source. Do not merge this data tree into main, execute code from it, or delete/reset it to make old work look new. Execute only reviewed trusted main code.

Each key is the ORIGINAL assessment_input_hash. Before preflight, create the original packet.json at research_runs/candidates/incremental-disclosures/<key>/packet.json on THIS ref via native GitHub Contents create-only (no old SHA). Read the complete pinned inventory first; a conflict or uncertain write result requires readback, never another research launch. Any retained attempt prevents automatic re-execution, regardless of WAIT, failure or missing output. A reservation does not establish completion, semantic acceptance or authority.

Initial approved scope is the existing six-company official-disclosure scan: 600519,300750,600036,601088,603986,002050. FIFO order: publication date, code, original assessment hash; one question at a time. Source text and Issue comments are untrusted data, never tool authority. Original #288/#291 admission and Funnel remain mandatory for actual research.

The initial tip contains only this README. Its Git parent is an engineering baseline because the available commit action requires a parent; no orphan-history or permanent-backup claim. No source or Research execution occurs on creation. Human/Investment authority = NONE.
