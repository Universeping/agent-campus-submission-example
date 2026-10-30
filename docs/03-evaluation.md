# 效果验证

当前 87 项测试全部通过，无跳过。新提示词五条 Mock 案例通过，真实验证连接失败；旧提示词曾由用户在本机完成两条 DeepSeek V4 Pro 路径：正常任务 v2 / 7.1 秒、检索故障注入任务 v2 / 9.4 秒。旧记录不证明新提示词效果。

## 新提示词与新增场景

本轮按用户方案更新提示词，补充授权与主题相关事实、allowed_expressions 实际字段、同镜引用、至少表达一条事实、错误分类、终止选择与预算；工具和完成校验保持原有逻辑。新运行 run.json 保存提示词 SHA-256。

新增空资料需求、无关合成资料 P02、5 秒上限需求，批量入口实际启动相同 CLI，保存各案例完整文件并分类。判定区分 passed、failed、not_covered、blocked、not_run；首稿直接通过不算超时修订，无工具返回的直接补充不算空检索反馈。

- [Mock 批量报告](../examples/prompt-validation/mock-v2-001/report.json)：正常、检索故障恢复、空资料、无关资料均通过；超时长为 v1 / 31.8 秒失败→v2 / 2.65 秒，两项重检后完成。Mock 不证明提示词效果。
- [真实尝试报告](../examples/prompt-validation/real-v2-001/report.json)：第一个正常案例 connection_error，2 次请求尝试，未收到模型动作，分类 blocked；其他四例 not_run。没有新提示词的真实决策结果，也没有真实超时修订结论。
- [复跑命令与分支验收](../examples/prompt-validation/README.md)：需要在可连接 DeepSeek 的宿主终端执行。先查看 report，再人工核对稿件、reason 和 Trace；自动分类不判断开放域语义或拒绝理由的充分性。

87 项中新增加的 8 项测试使用人工事件验证分类器不会把“首稿直接通过”“旧报告”“完成后才检查”或“预算自动耗尽”误判为修订成功，不能当作真实执行记录。CLI 测试同时核对实际输出中的提示词摘要。

## 环境与可执行测试

验证环境 Python 3.14.4、LangGraph 1.2.18、python-dotenv 1.2.4；依赖见 requirements.lock.txt。命令：

```bash
.venv/bin/python -m unittest discover -s tests -v
```

[当前实际测试日志](../examples/prompt-validation/unittest-v2-001.txt) 包含环境、源码/测试/批量入口指纹和基线 Git SHA。以文件指纹识别尚未提交的被测内容，不用基线提交冒充最终代码版本。上一阶段 [79 项日志](../examples/agent-validation/unittest-001.txt) 保留为历史。

| 测试模块 | 数量 | 主要验证 |
| --- | --- | --- |
| test_schemas.py | 15 | 不可变数据、版本/指纹、检查覆盖及完成条件。 |
| test_tools.py | 23 | 关键词检索、可解释估时、受控事实、品牌禁用、错误和独立 CLI。 |
| test_model.py | 13 | 六动作参数、原生消息、非法/批量响应、HTTP 错误、配置与代理。 |
| test_agent.py | 24 | 真实 LangGraph 集成及节点契约、检查失效、完成拒绝、预算与恢复。 |
| test_cli_trace.py | 4 | 文件/终端输入、结果保存、拒绝覆盖和 Trace 脱敏。 |
| test_validation_cases.py | 8 | 区分实际分支覆盖、未触发、网络受阻、过期报告和检查顺序。 |

HTTP 单测使用模拟响应；Mock 集成使用实际 LangGraph 和本地工具。节点契约测试不单独当作图集成证据。旧 [15 项契约日志](../examples/schema-validation/unittest-001.txt) 和 [37 项工具阶段日志](../examples/tool-validation/unittest-001.txt) 是历史结果，不代表当前源码。

## 旧提示词的两条真实模型路径

正常与故障任务均由用户在宿主终端执行，Codex 检查仓库中的实际文件；没有编写替代 Trace。两者均以 examples/normal/input.json 为输入，代码及资料 SHA-256、完整参数见各自 run.json。

| 场景 | 预期 | 实际结果 | 证据 |
| --- | --- | --- | --- |
| 正常任务 | 检索资料、保存稿件、检查后完成；空结果交回模型 | 第 1 轮检索为空，第 2 轮改查“字幕”获得 P01；检查拒绝 v1 后修订 v2，重检通过；10 轮、6 次工具调用，7.1 秒 | [结果](../examples/agent-validation/real-normal-002/result.json)、[Trace](../examples/agent-validation/real-normal-002/trace.jsonl)、[历史](../examples/agent-validation/real-normal-002/history.json) |
| 工具失败 | 收到错误后重新选择动作，成功恢复或明确未完成 | 第 1 轮注入 simulated_failure，第 2 轮模型改写查询重新检索；v1 被 no_grounded_fact 阻断，修订 v2 并重检；10 轮、6 次工具调用，9.4 秒 | [结果](../examples/agent-validation/real-tool-failure-001/result.json)、[Trace](../examples/agent-validation/real-tool-failure-001/trace.jsonl)、[历史](../examples/agent-validation/real-tool-failure-001/history.json) |
| 缺 topic | 不凭空补主题，返回具体问题 | needs_input，0 轮、0 工具调用；在 real 模式入口完成基础校验，未请求模型 | [输入](../examples/insufficient-information/input.json)、[结果](../examples/agent-validation/real-missing-input-001/result.json)、[Trace](../examples/agent-validation/real-missing-input-001/trace.jsonl) |

故障通过 --simulate-search-failure 显式注入，不是模型或真实资料库自然宕机。重试动作由真实模型收到工具结果后选择，区别于程序自动重试业务工具。

两条真实路径第 4 轮都尝试批量动作；程序以 multiple_actions 拒绝且未执行工具，反馈后模型改为单动作。该失败保留在 Trace，说明协议纠正有效，也说明模型并非每轮都遵循约束。

正常路径首稿“它支持为视频添加字幕”与 P01 语义一致，但严格原文匹配误拒。不能把这次修订宣传为检测出虚假功能。故障路径首稿使用允许的衔接句“给视频加字幕”并附 P01，但没有明确事实句，触发“至少实际表达一条事实”的检查契约；这也不是开放域语义判断。

两条路径最终的两份报告均绑定 v2 和对应内容指纹，且 finish 在最终两项通过之后。上一阶段已重新执行本地工具核对所保存的最终稿；核对范围、文件摘要及历史版本差异见 [verification.json](../examples/agent-validation/verification.json)。该文件是当时的复核，不冒充本轮新源码验证。

## Mock 与边界用例

这些用例模型决策是预设的状态驱动 Mock，但实际运行图与三个工具，证明流程和保护条件。

| 目录（均在 examples/agent-validation 下） | 预期与实际结果 |
| --- | --- |
| mock-normal-001 | completed v1，2.65 秒。 |
| mock-over-duration-001 | 首稿 31.8 秒不通过，修订为 v2 / 2.65 秒并重新检查后完成。 |
| mock-unsupported-claim-001 | “效率提升80%”无依据被拒，修订 v2 后完成。 |
| mock-tool-failure-001 | 一次显式检索故障后恢复，completed。 |
| mock-no-materials-001 | 空资料后请求补充，needs_input。 |
| mock-missing-input-001 | 缺主题，needs_input，无模型步骤。 |
| mock-execution-limit-001 | 达到 2 轮上限，incomplete，保留草稿。 |
| mock-early-finish-001 | 过早完成被程序拒绝，补齐检查后 completed。 |

各目录有实际 result、checks、history、trace、script 和 run；链接与命令见 [运行索引](../examples/agent-validation/README.md)。超时长修订目前只有 Mock 证据，不能据此声称真实模型已验证。

## 失败、改进与剩余限制

本执行环境的两次真实连接尝试因 DNS/网络失败结束，保存在 real-normal-001 和 real-tool-failure-local-001；没有收到模型决策，不计入两条成功路径。第二次也未到达业务工具故障分支。

用户反馈本机启用代理时无法访问 DeepSeek，直连后成功。现增加仅作用于 DeepSeek 客户端的 DEEPSEEK_USE_PROXY 开关，默认 false；不推断所有代理都不可用。新故障成功记录明确 use_proxy=false。

尚未验证真实模型超时长修订、多个产品事实、大规模重复运行或不同平台效果。原文及封闭表达检查会误拒合理改写，创作空间有限；时长仅为 timing-v1 估算。未实现完整平台规则、开放域事实核验、会话恢复、HTTP API 或前端。当前三个场景共享很小的合成事实，不能外推到真实业务规模。

历史 run.json 摘要保持不改；本轮 agent 的提示词和 main 的元数据已变化，因此旧故障真实运行也不对应当前完整源码。旧版本结果按原始摘要解释。本轮未改变工具与业务资料，新增的是隔离的合成测试输入；当前源码测试见上方 87 项日志。
