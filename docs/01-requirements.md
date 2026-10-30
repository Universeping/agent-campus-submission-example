# 需求与成功标准

业务理解基线 v0.1.0；当前已实现 CLI 单 Agent 最小闭环。79 项测试通过，保存了两条真实模型成功路径。完整效果范围及不足见 [评估](03-evaluation.md)。

## 用户、目标与范围

目标用户是将产品资料转化为短视频脚本的创作者。输入主题、受众、平台、目标时长和风格，输出可编辑的 JSON 与 Markdown：标题、分镜画面、旁白、每镜与总时长、来源、风险和状态。五项输入均必填；缺项则给出具体问题并结束，补充 JSON 后重新提交。

使用 Python CLI、LangGraph 1.2.18 单 Agent、DeepSeek V4 Pro、本地文本资料和三个工具。支持文件、stdin、终端粘贴 JSON。模型选择六个动作，程序执行并校验，首版不恢复会话。默认上限为 12 次模型请求和 8 次业务工具尝试。

时长是上限，不设置下限。timing-v1 使用 4 字符/秒、标点停顿、每镜至少 2 秒及转场；不代表实际配音。事实检查限定素材原文与封闭表达，会误拒合理改写；显式品牌禁用词可检查，任意自然语言规则与完整平台审核尚未实现。

暂不实现视频生成、配音、HTTP API、前端、多 Agent、会话恢复或生产级 Runtime。未形成真实平台规则数据集。题号与实际用时待候选人补充。

## 最小任务与资料

使用 [input.json](../examples/normal/input.json)、[materials.json](../data/materials.json) 与 [brand_rules.json](../data/brand_rules.json)。P01 仅含“支持为视频添加字幕”；B01 为“不得虚构功能或效果数据”。受众新手、轻松风格、30 秒以内。平台“通用短视频”是合成场景，无真实品牌归属。

成功标准：

1. 输出有标题、分镜、旁白、预计时长、来源和任务状态。
2. 产品事实得到 P01 支持，不能只验证来源 ID 存在；不扩展为自动识别、翻译、准确率或提效。
3. 最终估算时长不超过 30 秒，每镜与总时长可核对。
4. 完成前最终稿的估时和规则检查均通过，版本与内容指纹同时匹配。修改后真实重检，旧检查只保留为历史。

任务状态为 completed、needs_input、incomplete、failed，非完成必须说明原因。

## 验收对应关系

| 验收点 | 实现和测试 | 实际证据与边界 |
| --- | --- | --- |
| 完整脚本与正常闭环 | agent/main；test_agent、test_cli_trace | [真实正常结果](../examples/agent-validation/real-normal-002/result.json)，v2、7.1 秒。 |
| 缺关键信息 | prepare 校验与 questions | [缺输入结果](../examples/agent-validation/real-missing-input-001/result.json)，needs_input；0 次模型调用。 |
| 资料不足 | search、request_input | [空资料 Trace](../examples/agent-validation/mock-no-materials-001/trace.jsonl)，Mock 决策，请求补资料。 |
| 工具失败后调整 | 结构化错误反馈、模型重新决策 | [真实故障 Trace](../examples/agent-validation/real-tool-failure-001/trace.jsonl)，显式注入一次检索失败，模型重新检索。 |
| 超时长修订与重检 | estimate_duration、版本循环 | [超时长历史](../examples/agent-validation/mock-over-duration-001/history.json)，31.8→2.65 秒；仅 Mock，真实模型尚未验证此分支。 |
| 产品依据与引用 | 原文/受控表达、同镜引用、no_grounded_fact | test_tools；[真实修订 Trace](../examples/agent-validation/real-tool-failure-001/trace.jsonl)。不是通用事实判断。 |
| 稿次、时长、报告对应 | schemas 完成约束；agent 可信执行 | test_schemas、test_agent；两条真实路径均保存 v1/v2，最终只用 v2 两项报告。 |
| 两条真实动态决策路径 | model 原生函数调用、LangGraph 条件循环 | 正常路径空检索后改查询；故障路径收到工具错误后重新检索，两者均有检查反馈后修订。 |
| 执行预算与明确未完成 | 主动计数及图后备上限 | [上限结果](../examples/agent-validation/mock-execution-limit-001/result.json)，incomplete；test_agent 覆盖工具上限。 |
| 可复现、离线入口、可执行测试 | README、锁定依赖、CLI | [运行索引](../examples/agent-validation/README.md)、[79 项测试](../examples/agent-validation/unittest-001.txt)。 |

以上覆盖本轮最小业务范围；不将 Mock 分支视为真实模型效果，也不宣称已证明重复运行稳定性或自由创作质量。

## 后续资料准备

官方发布规范、产品事实、自定品牌/创作配置、合成案例须分开记录。抖音/快手规范可作为规则参考，剪映/必剪说明可作为产品事实候选。来源登记在 [sources.md](../data/sources.md)，登记不等于已经转成可执行检查。扩展范围时再补充有来源的数据与相应用例，不将经验性数值写成平台强制要求。
