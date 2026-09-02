# Next Chat Notice — 2026-09-02

请先阅读：`docs/HANDOVER-2026-09-02.md`。

然后直接继续当前工作，不要重新设计整个系统。

当前第一优先级：

1. 检查 PR #38 `feat: add one-shot official disclosure scan CLI`。
2. 写本通知时：PR open、mergeable、head `a0fcd01f3a42f8c7b3a24712891f4574d054290a`、CI **152 passed**。
3. 若状态仍一致，直接 squash merge。
4. merge 后不要立刻给 disclosure scan 加 daily scheduler；先定义并 dogfood 最小 Harness receipt / seen semantics，防止 `WAIT_FOR_TRIGGER` 的同一公告每天重复出现。

必须保持：

- Kernel owns truth. Harness owns motion.
- Research != Recommendation.
- Odds != Recommendation.
- Human 是最终 Investment Decision Owner.
- Radar = Research attention allocation，不是 stock picker。
- HiThink 是已锁定的 market-data source，不做 provider framework / fallback。
- 新 disclosure 不能直接 Human wake；先走 frozen Research freshness，再走 existing Research Funnel。

最近已证明的链：

`18 raw CNINFO announcements → 10 dated DisclosureBatch → 1 Research-uncovered CATL disclosure → official PDF / Evidence → existing Pre Research → WAIT_FOR_TRIGGER`

因此不要新造 Radar routing state machine。
