# Research-only model risk `NOT_ESTABLISHED` v0

Scope: #321-B historical/real Research freeze compatibility. Investment Authority = NONE.

Decision Kernel historically defaulted `ResearchSnapshot.model_risk_level` to `MEDIUM` because the original schema-v1 Decision Spine always expected a numerical Odds model. Human-origin Research-only schema v2 has a different legitimate state: the Research can be frozen while a scalar model-risk severity has never been assessed. Using the legacy default during a mechanical historical freeze would manufacture a judgment.

`ModelRiskLevel.NOT_ESTABLISHED` therefore means exactly:

> the frozen Research does not establish a LOW / MEDIUM / HIGH / VERY_HIGH scalar model-risk level.

It is **not** a fifth risk tier, not equivalent to MEDIUM or VERY_HIGH, and has no required-return addon.

## Allowed scope

`NOT_ESTABLISHED` is valid only for an explicit schema-v2 Research-only `ResearchSnapshot` with no `valuation_bases` and no canonical numerical `scenarios`. The normal Research-only accountability fields still apply: exact information identity, nonblank core thesis and model-risk notes, explicit invalidation/reopen conditions, PIT/source lineage, and COMMIT chronology.

The legacy default remains `MEDIUM`; existing schema-v1 objects and hashes are not migrated. A historical workpaper whose scalar model-risk level was never stated must explicitly use `NOT_ESTABLISHED` when mechanically frozen. It must not obtain `MEDIUM` merely because that is the old constructor default.

## Fail-closed boundary

Schema-v1 / Decision Spine and supplied canonical numerical state reject `NOT_ESTABLISHED`. Before canonical Odds can use the Research, a genuine Research/model revision must establish one of the original risk levels and preserve normal version/predecessor lineage. A price refresh cannot create that judgment.

Probability-free conditional-world analysis from `docs/conditional-odds-v0.md` may consume a committed schema-v2 Research-only snapshot with `NOT_ESTABLISHED`, because that adapter does not calculate a risk addon, calibrated probability, weighted aggregate or canonical participation zone.

This contract does not convert Markdown into Kernel Research, invent EvidenceArtifact identity, migrate Human acceptance, qualify a price, or create Watch/Action/Investment Authority. It only prevents an absent historical judgment from being silently replaced by the old MEDIUM default.
