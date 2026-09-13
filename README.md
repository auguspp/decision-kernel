# Decision Kernel

Decision Kernel is the small, explicit investment-decision core extracted from Decision OS.

It is **not** Decision OS v2 and it is **not** a new platform build.

## 公司研究 / Odds / 第一笔：新聊天从这里开始

**[打开统一研究执行入口](docs/RESEARCH-ENTRY.md)**。先固定当前 `main` commit，读取入口及案例更正，再接续 Research、估值、Odds 或买入价讨论；不要依赖旧聊天或搜索片段。根目录 [AGENTS.md](AGENTS.md) 指向同一入口。

入口复用已有 Decision Hygiene / Full Research Review Gate，不新增 Kernel 宪法或自动交易能力。光电旧 first-entry 梯度已标为待方法复核；恒瑞原 Human 接受记录保留，并补了完整下行的回放。**档案存在不代表已登记监控、已接受或已交易。** 未读取仓库的客户端不会自动获得这些规则。

## 股票阅读 · 历史已验收结果

**[打开 2026-09-07 完成交易日的已验收保存结果](docs/stock-reading-accepted-2026-09-07.md)** — 四家公司全部检查：神农集团一张观察卡，其余三家条件不满足，数据不可用零。

这是固定历史索引，不是实时行情或自动更新的最新结果中心；索引更新／核验日为 2026-09-08（UTC+08:00），不表示已自动检查今天有无更新。索引说明四家公司处置、通过／未通过原因和未覆盖范围，并提供原件入口；下载需仓库权限，解压后打开 `reading/index.html`。观察卡不是买入建议。

## Operating principles

1. **Own only investment cognition invariants.** PIT, exact lineage, frozen state identity, deterministic Odds inputs, Human accountability, authority boundaries, and Human-surface eligibility belong here when changing them would break the decision system itself.
2. **Research method is versioned policy, not constitution.** A useful research recipe can be strict without becoming a permanent Kernel invariant. `research_contract_v1.py` and `claim_audit_contract_v1.py` preserve current research-quality policy separately from Kernel commit authority.
3. **Reuse commodity infrastructure.** Market-data transport, news aggregation, HTTP, retries, scheduling, process supervision, logging, storage plumbing, and UI stay outside the core and should use mature tools/services with thin boundaries.
4. **Modular monolith, thin workflow.** Modules stay independently understandable; a small application workflow connects them. No plugin platform, event bus, provider framework, or orchestration framework by default.
5. **Quiet stop is a product outcome.** A workflow may deepen, wait, drop, stop quietly, or wake the Human. It does not need to run every stage.
6. **Human authority stays final.** Research, Odds, and Decision Rehearsal never become an autonomous investment decision, position size, portfolio action, execution instruction, or capital authority.
7. **Extract proven core; do not wholesale-copy the old repository.** Existing Decision OS implementations and tests are source material. Transitional plumbing stays behind unless it proves it belongs in the kernel.
8. **Reuse-first gate for new code.** Before adding non-unique infrastructure, check mature prior art first. A thin adapter is preferred to an owned subsystem.

## Constitution vs Research Contract

Use one hard test before adding or requiring a Research field:

> If this field disappears, does PIT, Belief, Odds, exact lineage, or Human accountability become invalid?

If yes, it may belong to the Kernel. If no, it belongs to a versioned research method, quality contract, or presentation layer until proven otherwise.

Examples:

**Kernel invariants**

- evidence cannot leak from the future
- frozen Research identity and hashes cannot silently change
- a Scenario distribution used by Odds must be complete and probabilities must sum to one
- Odds must use the exact committed ResearchSnapshot and exact market observation
- belief / market expectation / invalidation required by the Human decision surface remain explicit
- a ResearchSnapshot cannot be committed before its PIT cutoff or creation time
- investment authority remains `NONE`

**Decision OS Research Contract v1 policy**

- require FACT + INFERENCE + ASSUMPTION claim classes
- require variant perception and richer research narratives
- require fundamental / expectation / liquidity clock assessments
- require three to five monitoring indicators
- use a two-to-five-scenario research set
- require explicit scenario assumptions and financial drivers
- require bounded adversarial review

**Claim Audit Contract v1 policy**

- independently cover every exact material claim once
- verify FACT / MARKET_CONTEXT identity, period/date, units, source location, and evidence support
- require explicitly declared numerical assertions to be deterministically recalculated
- bind numerical Evidence inputs to exact structured EvidenceArtifact values
- require every numerical operand to have explicit provenance from Evidence or a declared literal with a reason

Claim Audit v1 deliberately does **not** infer authority from provider/source-name prefixes, parse prose with a numeric regex, or maintain a whitelist of magic calculation constants. Those are method/implementation choices, not Kernel law.

These research-quality rules can remain strict without gaining Kernel commit authority.

## Research method vs Decision Spine

The current Decision OS research recipe is one replaceable upstream method. Kernel commit authority also accepts a method-agnostic `ResearchCommitPackage` containing a REVIEW `ResearchSnapshot`, its exact `EvidenceArtifact`s, non-authoritative rehearsal framing, and a proposed commit time.

```text
Research Method v1 (replaceable policy)
    Discovery
       |
       v
    Pre Research -----> WAIT / DROP
       |
       v
    Quick Research ---> WAIT / DROP
       |
       v
    Deep Research
       |
       +--> Research Method v1 acceptance
       +--> Research Contract v1
       +--> Claim Audit Contract v1
       |      (quality assessments; no Kernel authority)
       |
       v
    ResearchSnapshot
       |
       +-----------------------------+
                                     |
Future / external research method    |
    REVIEW ResearchSnapshot          |
    + exact EvidenceArtifacts        |
    + non-authoritative framing      |
             |                       |
             v                       v
          ResearchCommitPackage / v1 package
                         |
                         |  Kernel commit authority
                         v
              COMMITTED ResearchSnapshot
                         |
                         v
Decision Spine (method-agnostic)
    ResearchSnapshot + ObservedMarket
       |
       v
    Odds
       |
       v
    Decision Rehearsal
       |
       v
    HumanResearchSurface
       |
       +--> quiet
       +--> wake Human
```

`research_workflow_v1.py` owns the current Discovery / Pre / Quick / Deep orchestration. `workflow.py` must not know those method stages; it composes only `ResearchSnapshot -> Odds -> Decision Rehearsal -> HumanResearchSurface`.

Research Method v1 acceptance validates only the current method's funnel, exact projection, evidence mapping, and package identity. Research Contract v1 and Claim Audit Contract v1 assess method quality. None of them decides whether a `ResearchSnapshot` is commit-ready. That authority stays in `ResearchSnapshot` / `commit_snapshot()`.

`research_commit.py` is the method-agnostic handoff. It requires the package Evidence set to match every Evidence/provenance reference in the ResearchSnapshot exactly, rejects Evidence unavailable at the snapshot PIT cutoff, and freezes the exact Kernel-visible research state into `information_bundle_hash` before commit.

A future Research Method v2 can therefore produce a valid `ResearchCommitPackage` and enter the same Decision Spine without changing `workflow.py` or pretending to be Research Method v1.

## Architecture watchpoints

Two current conveniences are intentional, but they do not gain semantic authority merely because they are convenient.

**`ResearchCommitPackage.framing`**

`framing` exists so one JSON file can run from reviewed research through Decision Rehearsal and the Human surface. It is executable context, not Research identity: `research_commit_information_bundle_hash()` excludes it. If a second ResearchCommitPackage consumer does not need rehearsal framing, prefer splitting the run context (or simply passing framing as a function argument) rather than turning this convenience into Research semantics.

**`live.py`**

`live.py` is the default executable composition root. It may wire security-id mapping, the default Odds policy, a supplied market fetch capability, and the Decision Spine. It must not accumulate provider fallback, retry/backoff, scheduling, case persistence, research routing, Radar logic, notification policy, or similar operating-system responsibilities. Those concerns belong in replaceable Harness code outside this composition root.

Architecture tests intentionally guard both boundaries. Adding a new local dependency to `research_commit.py` or `live.py` should require an explicit architecture decision rather than happening accidentally.

## Minimal live commands

Install once and provide the already-verified HiThink market-data credential:

```powershell
python -m pip install -e .
$env:HITHINK_FINANCE_API_KEY = "<your key>"
```

Run the preserved Decision OS Research Method v1 package:

```powershell
decision-kernel run .\path\to\deep-research-package.json
```

Or run any method-agnostic reviewed research handoff:

```powershell
decision-kernel run-research .\path\to\research-commit-package.json
```

Both commands fetch only the HiThink trading calendar and raw daily history needed for the security, require the raw history to reach the latest completed A-share session, apply the preserved `decision-os-live-odds-v0.1` policy, and print the same compact Human-facing result.

A normal quiet result is valid. `INSUFFICIENT_ODDS` does not wake the Human. Only `HumanResearchSurface.status + attention_eligible` controls Human attention. Investment authority remains `NONE`.

## Boundaries

```text
research method / external research
             |
             v
ResearchCommitPackage
    PIT + exact Evidence + identity
             |
             v
COMMITTED ResearchSnapshot
             |
runtime/hithink_http.py
    HTTP + API key + request construction
             |
             v
adapters/hithink.py
    provider payload qualification
             |
             v
ObservedMarket
             |
             v
workflow.py
    method-agnostic Decision Spine
```

Do not add by default:

- dashboard framework
- provider registry/framework
- fallback market provider
- retry/backoff framework
- scheduler framework
- process supervisor
- generic artifact service
- agent framework
- portfolio construction or sizing
- trade execution

The success condition is not feature parity with Decision OS. The success condition is a smaller, harder investment-decision core that is easier to run, replace around, and trust.
