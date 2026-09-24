# 普源精电正常新问题：质量与交付回执

日期：2026-09-24（Asia/Singapore）。这不是江西/振江历史实验续跑，也不是完整Full或投资结论。

## 实际完成

正常2026-09-23仪器仪表/Stock批次→公司问题rigol-h1-growth-profit-cash-conversion→完整2026H1及限定更正核验→原生main工作流的一次单Quick→原W保存→原Collector/Publisher发布→同版本读取和本轮Brief。选题与来源准备仍是受监督操作，自动日常选题及自然发布未签收。

#533只修改原有stock-question-request.json，M=5b8c07e49db21de1550ccc103294f6c079124ed9。PR与独立main完整测试均6109通过，原6109用例和依赖完全保留；没有扩展runtime、workflow、provider或日常配额。预研究普通publisher35937987461通过，但不将它算作本次研究交付。

真实研究run35938160978/attempt1成功，00:23:25.996485–00:24:46.584960Z仅一次Sub2API Quick，无Pre、retry/fallback/新取件/Full。请求模型gpt-6-astra；现有host未单独留存returned_model字段，不补称已独立核对上游权重。usage输入131059、输出2444、合计133503tokens；实际账单UNKNOWN。

W=fad48e9455ced9f0de4548a5950fc105aa725cda；17个Git留存文件由artifact原件独立重建为子树da61ac0d75494ce5f82c9eb71b6542c76a5c9185，匹配远端。quick-model-input.json只在原18文件artifact中，不误称已进入Git。candidate=9d8d9eb526adbd2edb6034cef1fe41ad78d6c751d880e82a5bb792691baec304，VALIDATED_QUICK_RESULT、COMPLETE、FULL_CANDIDATE；full-commission为不执行的委托。

## 来源及内容复核

原始CNINFO205页中报，PDF SHA256270adcca370bf047b1af3e54d64e78a11496549d7c720c15dc8c7f2114e2ed5a。完整435146字节context无截断，原源核验metadata在prompt/launch/最终回执相同。实际post-declaration目录和原件读回先于研究cutoff；不把过去核验延长为实时新鲜度。PDF未经审计；其他临时公告和估值不在范围。

已核对原模型raw/parsed/schema、Evidence allowlist、candidate/receipt重验；同R阅读的15份引用源文件长度、Git blob和SHA256均按原件核对。新无Pre显示NOT_APPLICABLE而非失败，旧江西失败与其他旧结果不改。

财务解释有两侧：扣非转正、毛利额增长及费用增长慢于收入支持真实经营改善；毛利率下降、存货等营运资本占用、受限资金释放及母公司/合并现金分化限制现金创造的强结论。不能用全部投资收益证明经营改善，也不把CFO减全部资本开支称严格股东自由现金。Full委托给出可推翻解释的具体工作，而不是凭未知数量升级。

**算术勘误：** 原文第三条主张“销售、管理和研发费用合计仅增加582.11万元”不准确。原PDF第28页：本期61317886.54+45455329.18+115651532.56=222424748.28元；上期58351596.87+49882850.44+108363247.61=216597694.92元；差额5827053.36元=582.705336万元，约582.71万元。原文不改，勘误随使用提供；差异不改变费用增速低于收入的方向，但结构通过并不保证数字正确。

已对保存文本/算术和部分PDF图像表格进行核对，非独立Human审计、非全财报审计或普遍方法优越性验证。不能声称全部主张和经济归因均已证明。

## 发布事实与两项未完成事项

研究完成后未观测到自动workflow_run发布，所以没有重跑研究。复用未经修改的原Collector和原atomic publisher作一次显式发布；refresh如实记录临时workflow/run/push及原研究run，未伪造正常自动事件。当前R=8fc9733a0f1ba0a514b10989a0c99fdc9737096e，reading_hash=9b2ceb24d2fd690581b8e37e75abf60125520f3853323b5e70866da13fba41e8。独立GitHub读取确认ref前移、同R README和研究详情已显示688337及正确候选；本地原validator复算reading_hash，源文件核对通过。

显式发布job35938981971最终为failure：原publish已完成，随后临时脚本用同一个memo化API.get读取可变ref，得到发布前缓存，导致line41 AssertionError。原日志/失败audit保留；不能把COLLECTED_NOT_PUBLISHED字段机械当作当前未发布，也不把job改绿。独立新读取确认实际发布，不再重发。这是临时交付后检查使用缓存不当，不需扩建恢复系统。

**仍未完成：** 自动研究→发布触发可靠性；正常批次全部处置的正式daily-review关联（当前NO_MATCHING_SAVED_DAILY_REVIEW，六对象审阅仍在原问题引用normal-batch-review.json中可追溯）。这次利用已有监督入口，不能冒充无人值守daily链或Industry全链验收。

原生Daily Brief任务6aa28013b7348191a647f2f8e75d6017经实际peek仍启用，每日19:15 Asia/Shanghai，v1.3按同R读取reviewed_question_work；未修改、重复创建或Run now。本文/本轮会话提供首次实际可读内容；未来自然送达、Human反馈及5–10真实交易日尚不能预填。R4-2产品出口、R4-2.5及P1未整体签收。

下一施工应集中在已暴露的自动发布和批次关联接点，复用原研究结果，不重新做单Quick/SDK迁移或重跑688337；随后按r4.1推进。#525仍停放、#531实验不合并，没有自动Full、Dashboard/P2或投资权限。
