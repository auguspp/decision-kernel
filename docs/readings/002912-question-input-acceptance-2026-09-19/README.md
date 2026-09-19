# 中新赛克真实问题接点验收｜2026-09-19

**结果：已保存一个真实来路的问题及预声明材料范围；原来源预检实际拒绝。完整 reviewed_question_input.prepare 正向验收未完成，Research／Pre／Quick均未执行。**

## 用户可读的问题

中新赛克（002912.SZ）2026年上半年收入、利润与经营现金流是否同向变化？如果分离，是交付/验收节奏、应收和存货占用，还是减值/一次性损益更能解释？哪些证据能够推翻对应解释？

这是限定历史财务桥的问题，不是判断2026年9月经营复苏，也不是解释机构动机。原机构观察的保存市场日为2026-09-17：供应商日涨跌-8.6294%、机构净额+28,812,452.2元。方向差异仅是研究起点；不能据此认为机构正确或股票应买入。没有该证券的保存Stock价格处置，不等于其机构来路被拒绝。

## 实际完成

1. 固定M=9fb100ac330d06a3448c4ddf2a16fa12fbe6abae、R=ead15d17e82f9487f76e78194b465331b64bb87d，恢复原来源和显式研究关系。当前读取与一次仓库检索未提供该证券旧问题，不代表全历史不存在。
2. 重新取得机构artifact10527564199，2,995,041bytes，SHA25649f6e2752a91b845d015b54bc678df850f66243fc3909c5e84f6b06e5971f9d2，CRC有效。原verify对8个真实payload零网络重放成功；33家公司，capture/projection hash均等于原件。归档复制原payload为平面institutional-*文件，未执行artifact里的源码TAR。
3. 问题与必需来源计划在Git commit faf3acfc9f7659d494b81d1493dfbcee0e900ef7保存，真实提交时间2026-09-19T12:29:16Z，在本次官网/披露来源预检之前。原question-plan.md未因获取失败改写。
4. 实际做两条官方域查询，未取得合格半年报正文；打开公司官网，确认其公告链接指向SZSE；随后点击这个官方链接，工具报告Timeout fetching。没有取得PDF定位或字节，没有切换HTTP请求头、反爬/重试，也没有开启下载探针。
5. 用原external_research_admission.check_preflight实际检查保存记录：SOURCE_PREFLIGHT_INCOMPLETE。两项STATIC必要类的BODY绑定均为空。缺少财务正文未被改成可选，也没有把官网首页或公告索引冒充财务BODY。

## 来源记录与时间限制

公司官网：https://www.sinovatio.com/ ，工具引用web:turn103726view0，投资者关系下公告发布链接。该页面只用于来源导航，不提供本问题所需财务报表。
官网指向的SZSE索引：https://www.szse.cn/disclosure/listed/notice/index.html?name=%E4%B8%AD%E6%96%B0%E8%B5%9B%E5%85%8B&stock=002912 ，工具引用web:turn800320view0。工具层超时不是已证实的源站HTTP状态；源站原因仍UNKNOWN。两条查询分别为“中新赛克 2026 半年度报告 site:cninfo.com.cn”和“中新赛克 2026 半年度报告 site:sinovatio.com”；结果不足以证明报告不存在。

source-preflight.json的started_at使用已保存计划的Git时间作为本次预检的先行边界；每条checked_at为本地检查这些实际返回记录的时刻，不伪造逐个远端请求时间。没有LATEST_INVENTORY穷尽声明。预检过期后不得复用为当前准入。

## 留存与未完成边界

原company-reading.json为3,204,683bytes，超过512KiB输入source上限；本例直接使用37,710bytes原机构观察，不需要扩预算或新增切片器。reading.json由原生Git复用原R的1060a6f8f1da49e2cb4ce1fb07763c9de23e51ab blob，185,688bytes，保持原件。它在connector中已读取，但本轮未物化其完整字节至本地执行环境，未声明独立计算其SHA256/reading_hash或跑完#453接口。

本轮已执行的只有旧机构数据重放和原来源预检；完整问题sidecar、完整输入packet、prepare正向运行、launch-time admission、模型调用均未完成。source-preflight拒绝不是Funnel WAIT/DROP，也不使其它公司研究失效。这里的Markdown只是已冻结问题底稿，不能被称为已验证sidecar或COMMITTED研究。

本地是851个blob核对过的历史源码树及#453模块，不是完整current-main checkout。相关原模块/指纹与已读版本一致，执行时网络被禁止；本轮不冒称新的全量CI或新的native runner验收。代码、工作流、依赖、旧Stock stable key和历史失败都未改动。

文件作为原生Git输入验收记录留存。索引登记、正常publisher和研究接纳各自独立，不在本文预填成功；完整远端目录读取与本地文件物化不是同一件事。原始输入计划保留，后续获得必要正文时复核原范围与旧研究关系；此时不为过关而换公司或放宽材料，不接Tushare、不重启公告工程。

这条问题当前停在“必要来源待补”，没有Human投资待办、监控或资本动作。AI Investment Authority=NONE。
