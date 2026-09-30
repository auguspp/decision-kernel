# B2标准通道首次真实单证券验收｜新城控股601155.SH

Human授权及本次范围见[#620/5902685171](https://github.com/auguspp/decision-kernel/issues/620#issuecomment-5902685171)：由施工方任选一家公司验证。选择原六股之外、已有资料引用的601155.SH，报告期2026-09-30；这是工程样本，不是新增关注、持仓、Watch或投资接受。

## 来源与原件

原工作流[b2-disclosure-appointments run36658570687/1](https://github.com/auguspp/decision-kernel/actions/runs/36658570687)于2026-09-30T02:10:06—02:10:28Z完成，状态success；代码M=3ebb5d8456a8f6d544d329d0fcc9e0691b26bee7。只有一次巨潮getPrbookInfo POST，零重试/分页/重定向/换源，无业务凭证。原artifact11073600541为9206bytes，SHA256=4a072d7a4efb7a130adac914ebef05e2244a96cb16bda11c68cff338731e5a6f；已实际下载并检查大小、digest、ZIP CRC和成员安全。

八个原始输出文件逐字节保留；本README是后续说明，不是捕获原件。逐股摘要见[601155.SH/summary.md](601155.SH/summary.md)，原始返回见[response.body](601155.SH/response.body)，查询与HTTP时钟见[receipt.json](601155.SH/receipt.json)。原整批plan与单股plan一致；只有一个显式选择，不是全索引查询。

## 本轮字段核对与限制

原返回HTTP200，完整正文290bytes，SHA256=1f2b3692e35f9f59110b32f3b94abf1fb0e6679d701f7a7477c23574d5ff1a09。seccode=601155、secname=新城控股、f001d_0102=2026-09-30与请求和原登记身份相符；totalRows=1、totalPages=1，前后页标记均false。本次巨潮接口记录的首次预约f002d_0102为2026-10-31。三个变更槽f003d_0102至f005d_0102和实际披露f006d_0102均为空字符串；latest_time为null，orgId原值GD012027。

这是官方接口此次返回的首次预约字段，不是最终日、实际披露、完整改期史或独立来源确认。没有取得财报PDF或重算Research/Odds。公开网页检索未提供可独立核实该预约的记录，页面打开也未取得正文；不以相关新闻补证。字段核对不回写原捕获的NOT_PERFORMED/official_appointment_qualified=false或原摘要中的阶段性限制。

## 标准保管与后继读取

沿原生成的registration-proposal登记草稿操作：先保存全部原件并读回实际保管commit A，再只把新增引用的source.ref绑定A，追加至原current_state/registry.json。原草稿仍保持未绑定，不伪装成捕获时已完成登记。既有R4、全部Research/Human引用、源失败、宏观与任务配置不替换。

正常PR、独立main、自然publisher及固定R正文/逐股全目录读取分别在#620与本次PR留存；本README自身不提前宣称这些步骤完成。新增公司未要求改caller、workflow、reader或测试；首个真实使用检验的是既有通道而非新增机制。Investment Authority=NONE。
