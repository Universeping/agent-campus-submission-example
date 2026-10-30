# 项目代码

六个动作的单 Agent、DeepSeek 适配和 CLI 已实现，使用 LangGraph 1.2.18。字段见 [数据约定](../docs/06-data-contracts.md)，工具边界见 [工具说明](../docs/07-tools.md)，循环协议见 [Agent 文档](../docs/08-agent-loop.md)。

| 模块 | 职责 |
| --- | --- |
| main.py | 文件/终端输入，启动任务，保存六类输出文件及退出码。 |
| schemas.py | 不可变领域数据、版本/指纹绑定和完成约束。 |
| model.py | 配置、六动作 description/JSON Schema、标准 HTTP 客户端及离线 Mock。 |
| agent.py | prepare/call_model/dispatch/finalize 图节点、可信状态、历史版本和预算。 |
| tools.py | 实际关键词检索、明确假设的估时、受控事实及品牌规则检查。 |
| trace.py | 实际事件 JSONL 和凭据/内部推理过滤。 |

入口：`.venv/bin/python -m src.main --mode mock --input examples/normal/input.json`。真实调用使用 --mode real 和本地密钥。默认只对 DeepSeek 直连，不改变系统代理。

模型自主选择业务动作，程序执行和裁决；不执行模型任意代码，不接受自报报告。当前不含前端、HTTP API、视频生成、持久化会话或开放域事实核验。
