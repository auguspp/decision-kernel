# HiThink standard-index ticker alias contract — 2026-09-04

Status: **REAL PROVIDER CONTRACT CORRECTION / EXACT THSCODE REMAINS AUTHORITATIVE / NO FALLBACK / NO INVESTMENT AUTHORITY**

## Observed reality

The current-breadth operations proof returned these safe identity fields from the index snapshot endpoint:

```text
000001.SH -> ticker 1A0001
000300.SH -> ticker 1B0300
399001.SZ -> ticker 399001
399006.SZ -> ticker 399006
881101.TI -> ticker 881101
```

Source lineage:

```text
workflow run = 33890792134
artifact = 9943794625
artifact digest = sha256:b2f7f8cf6dde0bf4fdf39c6515155341a69a0ddd261504148faa1904597e7912
```

The exact requested and returned `thscode` values were correct. The redundant provider `ticker` metadata is not uniformly equal to the first six characters of `thscode` for Shanghai standard indices.

## Accepted adapter rule

```text
exact requested / returned thscode
= canonical index identity

standard .SH / .SZ ticker
= preserved six-character provider metadata

formal .TI industry ticker
= must equal thscode six-digit code
```

Malformed ticker metadata still fails closed. Exact request-set equality, duplicate checks, market-value validation, completed-session qualification and benchmark close matching remain unchanged.

This correction does not introduce a provider fallback, stale-data substitution, Research route, Human wake, Recommendation, Action, or investment authority.
