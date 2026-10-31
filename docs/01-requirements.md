# 需求与成功标准

业务理解基线 v0.1.0；当前已实现 CLI 单 Agent 最小闭环。119 项测试通过（105 项业务测试、14 项独立连接诊断测试）；8 个产品/客户端配置已接入，39 条事实启用、1 条暂缓，规则为项目自定演示政策。真实正常生成、缺关键信息、空资料、无关资料和工具失败处理均有记录。超时长案例已展示反馈后的修订、重检与明确未完成退出，尚未证明最终修订成功。当前结论及证据边界以 [评估](03-evaluation.md) 为准。

## 用户、目标与范围

目标用户是将产品资料转化为短视频脚本的创作者。输入主题、受众、平台、目标时长和风格，输出可编辑的 JSON 与 Markdown：标题、分镜画面、旁白、每镜与总时长、来源、风险和状态。五项输入均必填；缺项则给出具体问题并结束，补充 JSON 后重新提交。

使用 Python CLI、LangGraph 1.2.18 单 Agent、DeepSeek V4 Pro、本地文本资料和三个工具。支持文件、stdin、终端粘贴 JSON。模型选择六个动作，程序执行并校验，首版不恢复会话。默认上限为 12 次模型请求和 8 次业务工具尝试。

时长是上限，不设置下限。timing-v1 使用 4 字符/秒、标点停顿、每镜至少 2 秒及转场；不代表实际配音。事实检查限定素材原文与封闭表达，会误拒合理改写；显式品牌禁用词可检查，任意自然语言规则与完整平台审核尚未实现。

暂不实现视频生成、配音、HTTP API、前端、多 Agent、会话恢复或生产级 Runtime。未形成真实平台规则数据集。选题为第 4 题；候选人自报实际投入约 3.5 小时，中途有吃饭、睡觉暂停，未提供分阶段计时。个人贡献与复盘见 [AI 使用记录](04-ai-usage.md)、[复盘](05-retrospective.md)。

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
| 完整脚本与正常闭环 | agent/main；test_agent、test_cli_trace | [当前 CapCut 结果](../examples/data-validation/real-capcut-web-002/result.json)，v1、21.4 秒；[必剪结果](../examples/data-validation/real-bcut-ios-001/result.json)，v1、13 秒。 |
| 缺关键信息 | prepare 校验与 questions | [缺输入结果](../examples/data-validation/real-baseline-missing-input-001/result.json)，needs_input；0 次模型调用。 |
| 资料不足 | search、request_input | [真实空资料 Trace](../examples/data-validation/real-baseline-no-materials-001/no-materials/trace.jsonl)，实际检索后请求补充。 |
| 工具失败后调整 | 结构化错误反馈、模型重新决策 | [当前真实故障 Trace](../examples/data-validation/real-baseline-tool-failure-001/tool-failure/trace.jsonl)，注入错误后模型重新选择查询，成功恢复。 |
| 超时长后的修订或明确失败 | estimate_duration、版本循环、未完成退出 | [真实超时历史](../examples/data-validation/real-baseline-over-duration-001/over-duration/history.json)，7.6→5.3→2.25 秒，v3 无事实被拒，v4 保存后预算耗尽未检；任务 incomplete，自定义评估 failed。有修订和失败退出证据，无最终修订成功证据。 |
| 产品依据与引用 | 原文/受控表达、同镜引用、no_grounded_fact | test_tools；[当前真实规则反馈](../examples/data-validation/real-baseline-over-duration-001/over-duration/trace.jsonl) 拒绝只引用 P01 却不表达事实的 v3。不是通用事实判断。 |
| 稿次、时长、报告对应 | schemas 完成约束；agent 可信执行 | test_schemas、test_agent；当前两条产品成功结果仅使用各自 v1 报告；超时长 v4 不沿用 v3 通过报告。[历史 v2 重检](../examples/agent-validation/real-normal-002/history.json) 单独保留。 |
| 两条真实动态决策路径 | model 原生函数调用、LangGraph 条件循环 | [故障后改查并完成](../examples/data-validation/real-baseline-tool-failure-001/tool-failure/trace.jsonl)；[多次空检索后请求补充](../examples/data-validation/real-baseline-no-materials-001/no-materials/trace.jsonl)。均为当前业务源码的真实模型记录。 |
| 执行预算与明确未完成 | 主动计数及图后备上限 | [真实上限结果](../examples/data-validation/real-baseline-over-duration-001/over-duration/result.json)，incomplete；test_agent 另覆盖工具上限。 |
| 可复现、离线入口、可执行测试 | README、锁定依赖、CLI | [当前运行索引](../examples/data-validation/README.md)、[119 项测试](../examples/network-validation/unittest-003.txt)。 |

当前正常与异常路径记录见 [资料与真实运行索引](../examples/data-validation/README.md)。[提示词阶段索引](../examples/prompt-validation/README.md) 保留历史报告及仍可使用的批量入口说明，不再代表当前效果缺失。首稿直接短于上限不证明超时修订；没有实际空检索的直接补充也不证明观察空结果后的决策。

原题允许超时后修订或明确失败。当前案例可作为修订尝试及达到上限后明确未完成的记录；它没有证明模型主动判断业务约束无法满足，也没有证明最终稿成功。自定义评估器要求重检完成或模型主动 finish(incomplete)，因此原报告 failed 保留；该分类不直接等同于考核整项不达标。completed 的检查标准保持不变。

不将 Mock 分支视为真实模型效果，也不宣称已证明重复运行稳定性或自由创作质量。

## 后续资料准备

官方发布规范、产品事实、自定品牌/创作配置、合成案例须分开记录。抖音/快手规范可作为规则参考，剪映/必剪说明可作为产品事实候选。来源登记在 [sources.md](../data/sources.md)，登记不等于已经转成可执行检查。扩展范围时再补充有来源的数据与相应用例，不将经验性数值写成平台强制要求。

资料扩充已通过用户包接入 CapCut、Canva、Adobe Express、必剪 iOS，详见 [资料评估](09-data-pack.md)。产品客户端不等同于发布 platform；P01 保留作合成基线。8 条 Mock CLI 验证资料、范围、规则与来源可运行，但不证明真实模型选择最相关功能。业务成功标准未放宽，官方发布平台规则仍未实现。

当前宿主两条正常运行及 P01 批量连接失败见 [归档索引](../examples/data-validation/README.md)。产品稿件均 v1 一次检查通过，不能作为超时修订证明。缺资料与工具失败当前真实结果已独立补齐；超时长虽有数值反馈和修订，仍未完成最终重检及结束申请。

20/10 预算复跑超时长任务在最初两次请求连接失败，0 次工具，不能判断较大预算的修订效果。独立诊断已记录宿主 GET 列表成功和 POST 超时，详见 [记录](../examples/network-validation/README.md)。诊断不替代业务验证，也不是当前材料收尾的前置条件。
