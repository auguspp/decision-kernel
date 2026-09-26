## 2026-09-26 已完成采集与旧 pending 元数据对账

现场 R182c1ede0c35e077fa025e7dd31a1f09a1a94c5f（publisher36219048914）仍显示
AWAITING_CURRENT_CAPTURE，但原补采36217120177与后继对账36219031726均已完成。
不重抓市场、不把collection/触发通知的success替代原件资格。
当精确run GET仍是pending时，只额外读取一次GitHub原生
`actions/runs/<id>/attempts/1`；run、head、仓库、分支、workflow、event、attempt和
创建时间必须相同，更新时间不倒退/未来。仍pending继续等待；不一致/读取失败保留缺口。
完整attempt仍经过原jobs、artifact、原字节重放和历史合成，不放宽任何来源资格。
两次元数据的状态、更新时间与核对时点保留于overview；不据此猜网络缓存原因。
这是既有读取器的有限恢复，不增加数据采集、轮询、scheduler、权限或依赖。

复用依据：当前read_run/control、GitHub官方REST workflow run attempt接口
(https://docs.github.com/en/rest/actions/workflow-runs#get-a-workflow-run-attempt)；
现有GitHub客户端与原pytest fixtures。只修已证实交付缺口，不重建SDK/缓存框架。
自然后继和正式publisher读回单列验收，合成测试不冒充本次已恢复生产。

外部代码对照：PyGithub/PyGithub@9152817c2d437282d46e7822e825dcf7e3a3e947
`github/WorkflowRun.py::get_attempt`及`tests/WorkflowRun.py::testGetAttempt`，
均采用同一原生attempt端点并保留run ID/attempt身份；不引入PyGithub依赖或复制SDK。
