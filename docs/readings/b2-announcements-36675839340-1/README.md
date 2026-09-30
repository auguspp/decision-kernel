# B2：同一标准通道的真实非空公告目录

本说明独立于11份原始捕获输出，不修改其字节、状态、原始登记草稿或时钟。范围及后继接点归[#620/5905077823](https://github.com/auguspp/decision-kernel/issues/620#issuecomment-5905077823)、[5905111702](https://github.com/auguspp/decision-kernel/issues/620#issuecomment-5905111702)。Git保管、登记、发布及固定R恢复另见本次资料PR的实际回执，不由本说明预先认证。

## 实际来源

既有资料引用601155-xincheng-policy-full-20260930，601155.SH；公告发布日期窗口2026-08-26至2026-08-27（Asia/Shanghai）。source run36675839340/attempt1在代码b7119635ae62d75335c75a6820a478fbffe6a54f运行，未修改脚本、参数构造或来源解析器。两次HTTPS POST完成组织码与单页目录查询，无重试、重定向、备用源或额外分页。

原artifact11080530188：11570bytes，SHA256 c197eb072f0451d66f5dd79a7391e099714c455d8264f71e138f6a16664b240e；已核大小、digest、ZIP CRC、11文件及运行身份。原始目录query-2.body为2054bytes，SHA256 de603d047e823f97300c0418d5f16d30e292f3778c69b8c9ffc805e9f3263f5c。

原JSON的证券601155、组织码GD012027与三条公告匹配：1225512314半年报摘要、1225512308半年报、1225512248对外担保进展；来源公告时间均为2026-08-27T00:00:00+08:00。该时间不是正文事件实施日，也不据午夜字段推精确首发时刻。原totalAnnouncement=3、hasMore=false、totalpages=0全部保留，不修写来源元数据。原announcementType代码存在，announcementTypeName=null；现役解析器的announcement_type取后者，不能把派生null解释为原页没有类型代码。

原组织码及页解析器已在本次真实JSON字节上离线核对，三条身份、标题、时钟和定位与捕获结果一致；这不是新HTTP或本地全仓检查。真实非空单页成立，不证明真实多页、全历史、全市场或任何经济结论。原CAPTURED_REQUIRES_SOURCE_REVIEW、pdf_requests=0及未绑定registration-proposal保持原样；实际采用时仅在原registry后继条目绑定已核保管commit。

## 单独的PDF取得缺口

目录取得之后，仅选择1225512314《新城控股2026年半年度报告摘要》：https://static.cninfo.com.cn/finalpage/2026-08-27/1225512314.PDF 。摘要不是完整半年报。两个交互工具尝试均未取得文件：container.download返回通用download failed，web.open返回Cache miss；无PDF字节或可核HTTP状态，失败原因UNKNOWN，不称源站403、权限拒绝或PDF损坏。文件检查亦未发现目标PDF。

这些交互尝试不是上述Actions目录捕获中的PDF请求，不能回写原pdf_requests=0；也没有执行仓库cninfo_http的PDF getter、提取器或生产扫描。未取得、未保存、未渲染、未阅读PDF，不补正文事件日期、财务数字或实施状态。后继应沿现成有界PDF获取/保管能力解决实际使用缺口，不能重查已消费目录、换源掩盖失败或启动旧六股研究扫描。

## 保留边界

本目录不覆盖原9月24日至30日的空返回档案、预约36658570687、旧Full、Human回应、R4或其他用途。只使用原NAVIGATION_ONLY/RETAINED_FILES/ON_DEMAND_ARCHIVE登记路径；不自动关注、持仓、Watch、Research、通知或投资接受。无新运行代码、数据库、股票池、调度、依赖、权限或CI规则。Investment Authority=NONE。
