# Decision Inbox v0.1

Decision Inbox is the first Human-facing shell around the existing `HumanResearchSurface`.

It does **not** create a second attention policy. A case appears in the attention section only when the Kernel already produced `HumanResearchSurface.attention_eligible == true`.

## Normal use

The GitHub Actions workflow `decision-inbox` runs automatically on A-share weekdays after the market close. It batches the checked-in `dogfood/*.json` research cases through the existing HiThink live path and produces one consolidated Human summary.

The intended Human loop is:

```text
open latest Decision Inbox
        |
        +--> no attention cases -> close it
        |
        +--> attention case(s) -> inspect why now / belief / market expectation /
                                  open questions / invalidation / monitoring triggers
```

Quiet cases are collapsed by default. `HUMAN_ATTENTION_REQUIRED` is a request for Human review, not a recommendation or investment decision. Investment authority remains `NONE`.

## Manual use

The scheduled workflow can also be run manually from GitHub Actions. For a local or ad-hoc batch:

```bash
decision-kernel build-inbox dogfood/*.json
```

This writes:

- `decision-inbox/index.html` — dependency-free, mobile-friendly static snapshot
- `decision-inbox/summary.md` — the same Human surface for GitHub Actions Job Summary

The existing `live-dogfood` workflow remains useful for debugging or replaying one package. It is no longer the intended everyday Human entry point.

## Boundary

Decision Inbox is presentation/runtime Harness. It may render and order existing Human surfaces, but it must not decide whether a case deserves attention, alter Odds thresholds, create investment authority, route research, persist case state, or grow notification policy.
