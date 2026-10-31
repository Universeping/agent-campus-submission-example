# 效果验证

本文件汇总当前效果结论；各阶段的原始报告、Trace 和测试日志保持原样。最新 [119 项测试日志](../examples/network-validation/unittest-003.txt) 全部通过，无跳过，其中 105 项业务测试、14 项独立连接诊断测试；不等于 119 次真实模型验证。

当前真实正常路径为 CapCut 网页端 v1 / 21.4 秒、必剪 iOS v1 / 13 秒；缺关键信息、工具失败、空资料、无关资料均有实际记录。5 秒例已展示超时反馈后的修订、重检和明确未完成退出，尚未证明最终修订成功。20/10 预算复跑在最初两次请求均连接失败，没有检验较大预算的业务效果。

核心实现及主要场景已有证据。当前交付仍需补齐候选人实际用时、个人学习与独立尝试、题号，并将最新文档和证据提交推送后取得最终 SHA；不宣称全部验收均已无争议通过。前端、数据库、向量检索、会话恢复和继续网络诊断均不是本次材料收尾的前置条件。

## 产品资料扩充

原包 40 条事实、20 条项目规则、8 个配置，经审阅启用 39 条、隔离易混淆的 P_CAN_010。原包 62 个内容摘要全部匹配。[原始包复跑 140 项检查](../examples/data-validation/raw-pack-report.json) 全部通过，其中包含确认混合库缺少产品隔离的已知限制；它们不是 140 个业务或模型成功案例。

[8 次 Mock CLI 清单](../examples/data-validation/mock-runs.json) 全部 completed，实际时长 5.4、6.15、5.65、7.4、4.65、7.9、10.65、3.65 秒；每例保存同稿检查、Trace 和来源。资料接入阶段新增 18 项配置测试，当时共 105 项，后续独立诊断增加至 119 项。Mock 预设选择首条事实，不证明主题完整覆盖或创作质量。[早期真实 CapCut 尝试](../examples/data-validation/real-capcut-web-001/result.json) connection_error，后续宿主成功记录见下文。

范围规则为项目字面禁用项，可能误拒合理否定/比较；完整来源核对、复跑与限制见 [资料说明](09-data-pack.md)、[当前证据](../examples/data-validation/README.md)。旧 [87 项日志](../examples/prompt-validation/unittest-v2-001.txt) 是历史源码证据。

## 宿主真实验证补充

用户提供的两次产品运行及批量报告已原样归档，详见 [运行索引](../examples/data-validation/README.md) 和 [摘要/工具复核](../examples/data-validation/real-host-verification-001.json)。全部源码/资料摘要与当前代码匹配；两个最终稿的估时和规则报告均重新计算一致，检查发生在同稿保存之后、完成之前。

| 案例 | 结果与实际动作 |
| --- | --- |
| [CapCut 网页端](../examples/data-validation/real-capcut-web-002/result.json) | 8 轮、3 次业务工具，使用三条字幕事实，21.4 秒；一次批量动作被拒、两次间歇连接错误后恢复。 |
| [必剪 iOS](../examples/data-validation/real-bcut-ios-001/result.json) | 6 轮、3 次工具，使用字幕/文本朗读事实，13 秒；一次批量动作被拒后继续。 |
| [P01 批量](../examples/data-validation/real-baseline-batch-001/report.json) | normal 两次模型请求连接失败，每次约 60 秒，0 次业务工具；保护性停止后其余四例 not_run。 |

两条成功均为 v1、检查一次通过，不证明超时长后的修订。缺素材和业务工具失败的当前证据来自下文的独立复跑。网络错误恢复由程序重试完成，不作为模型自主决策；原业务 Trace 只有 connection_error，不能把该次失败归因于代理、业务资料、鉴权或限流。

人工质量观察：必剪标题仍只强调字幕，未突出旁白已包含的朗读功能，衔接文案受封闭列表限制。程序约束通过与主题/风格完整适配分别评估。两次都出现 multiple_actions，不能宣称单动作提示词已彻底解决协议遵循问题。

## 独立真实分支复跑

宿主随后逐个执行四例，原报告与 Trace 原样归档，详见 [索引](../examples/data-validation/README.md) 和 [复核摘要](../examples/data-validation/real-branches-verification-001.json)。评估器原判定经当前实现重新计算一致，没有修改 passed/failed。

| 场景 | 结果与观察 |
| --- | --- |
| [工具失败](../examples/data-validation/real-baseline-tool-failure-001/report.json) | passed，8 轮/5 次工具。注入错误→改查无结果→缩短关键词取得 P01→生成并检查完成，9.4 秒。 |
| [空资料](../examples/data-validation/real-baseline-no-materials-001/report.json) | passed，5 轮/4 次工具。四次真实空检索后请求补资料，未生成无依据稿件；空授权范围仍反复检索是效率限制。 |
| [无关资料](../examples/data-validation/real-baseline-unrelated-materials-001/report.json) | passed，4 轮/3 次工具。只授权 P02，改写查询仍为空，请求字幕素材。 |
| [5 秒超时长](../examples/data-validation/real-baseline-over-duration-001/report.json) | failed，任务 incomplete，12 轮/6 次工具。v1 7.6 秒、v2 5.3 秒均超时；v3 2.25 秒却无实际产品事实，规则拒绝；第 11 轮保存 v4 后，第 12 轮连接错误，用完步骤，无最终检查/finish。 |

超时长例说明模型会根据数值反馈压缩，但压缩曾丢失必要事实。一次批量动作拒绝、一次连接错误及多次修订消耗预算。最终 v4 的两项报告均为空，程序保留 incomplete，没有复用 v3 的通过结果或误报完成。

需区分三个结论：原题允许超时后修订或明确失败；当前记录证明了修订尝试、重检及达到上限后明确未完成；自定义评估器额外要求最终重检完成，或模型主动 finish(incomplete)，因此报告仍为 failed。该分类不直接等同于考核整项不达标，也不能把预算停止解释为模型已证明业务约束无法满足。真实模型最终修订成功尚未得到证明，completed 标准未放宽。

审阅时独立离线计算 v4 为 2.25 秒且规则通过，仅用于判断最终草稿可行，存放 post_run_diagnostics；这不是模型观察，不能补写到原 Trace 或把原任务改为 completed。原始结果与默认 12/8 预算保持不变。

另在当前代码执行 [缺 topic 的 real 模式入口](../examples/data-validation/real-baseline-missing-input-001/result.json)，needs_input、0 模型调用，属于输入校验，不包装成模型决策。

## 扩大预算后的连接阻断

[新复跑](../examples/data-validation/real-baseline-over-duration-002/result.json) 明确记录 20 步/10 工具预算，但只执行两次模型请求，每次约 60 秒后 connection_error；没有模型动作、工具或稿件。[复制与摘要复核](../examples/data-validation/real-over-duration-retry-verification-001.json) 通过。它不是又一次“模型压缩失败”，也不是预算耗尽。

独立诊断的 GET、POST 和阶段计时结果集中见文末及 [网络记录](../examples/network-validation/README.md)。它们没有修改 Agent 行为，不替代业务验证；继续定位网络不是本次交付的前置条件。

## 历史阶段：提示词与新增场景

该阶段按用户方案更新提示词，补充授权与主题相关事实、allowed_expressions 实际字段、同镜引用、至少表达一条事实、错误分类、终止选择与预算；工具和完成校验保持原有逻辑。此后运行的 run.json 保存提示词 SHA-256。

新增空资料需求、无关合成资料 P02、5 秒上限需求，批量入口实际启动相同 CLI，保存各案例完整文件并分类。判定区分 passed、failed、not_covered、blocked、not_run；首稿直接通过不算超时修订，无工具返回的直接补充不算空检索反馈。

- [Mock 批量报告](../examples/prompt-validation/mock-v2-001/report.json)：正常、检索故障恢复、空资料、无关资料均通过；超时长为 v1 / 31.8 秒失败→v2 / 2.65 秒，两项重检后完成。Mock 不证明提示词效果。
- [真实尝试报告](../examples/prompt-validation/real-v2-001/report.json)：该次正常案例 connection_error，2 次请求尝试，分类 blocked；其余四例 not_run。这份历史报告没有真实决策结果；当前正常及异常路径已由上文独立记录补充。
- [复跑命令与分支验收](../examples/prompt-validation/README.md)：说明仍可使用的入口及自定义判定。自动分类不判断开放域语义或拒绝理由的充分性，须结合稿件、reason 和 Trace 阅读。

87 项中新增加的 8 项测试使用人工事件验证分类器不会把“首稿直接通过”“旧报告”“完成后才检查”或“预算自动耗尽”误判为修订成功，不能当作真实执行记录。CLI 测试同时核对实际输出中的提示词摘要。

## 环境与可执行测试

验证环境 Python 3.14.4、LangGraph 1.2.18、python-dotenv 1.2.4；依赖见 requirements.lock.txt。命令：

```bash
.venv/bin/python -m unittest discover -s tests -v
```

[业务接入阶段 105 项日志](../examples/data-validation/unittest-001.txt) 包含环境、源码/测试/审阅配置指纹和基线 Git SHA。以文件指纹识别尚未提交的被测内容，不用基线提交冒充最终代码版本。上一阶段 [79 项日志](../examples/agent-validation/unittest-001.txt) 保留为历史。

| 测试模块 | 数量 | 主要验证 |
| --- | --- | --- |
| test_schemas.py | 15 | 不可变数据、版本/指纹、检查覆盖及完成条件。 |
| test_tools.py | 23 | 关键词检索、可解释估时、受控事实、品牌禁用、错误和独立 CLI。 |
| test_model.py | 13 | 六动作参数、原生消息、非法/批量响应、HTTP 错误、配置与代理。 |
| test_agent.py | 24 | 真实 LangGraph 集成及节点契约、检查失效、完成拒绝、预算与恢复。 |
| test_cli_trace.py | 4 | 文件/终端输入、结果保存、拒绝覆盖和 Trace 脱敏。 |
| test_validation_cases.py | 8 | 区分实际分支覆盖、未触发、网络受阻、过期报告和检查顺序。 |
| test_profiles.py | 18 | 39 条事实、人工样例、来源/范围、必需规则、隔离条目、实际图与 CLI。 |
| test_connection_diagnostic.py | 14 | 包装错误分类、HTTP 响应处理、模型列表与代理复用、报告凭据过滤。 |

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

各目录有实际 result、checks、history、trace、script 和 run；链接与命令见 [历史运行索引](../examples/agent-validation/README.md)。完整超时修订成功目前只有 Mock 证据；当前真实运行已观察到修订与重检，但最终稿尚未完成检查，不能混为一谈。

## 失败、改进与剩余限制

本执行环境的两次真实连接尝试因 DNS/网络失败结束，保存在 real-normal-001 和 real-tool-failure-local-001；没有收到模型决策，不计入两条成功路径。第二次也未到达业务工具故障分支。

用户反馈本机启用代理时无法访问 DeepSeek，直连后成功。现增加仅作用于 DeepSeek 客户端的 DEEPSEEK_USE_PROXY 开关，默认 false；不推断所有代理都不可用。新故障成功记录明确 use_proxy=false。

当前仅 CapCut 网页端和必剪 iOS 两个 profile 有真实正常成功记录，其余六个配置仅有 Mock CLI 验证；不能外推全部配置的真实效果。真实模型超时长最终修订成功、大规模重复运行稳定性和不同发布平台的适配效果尚未证明。原文及封闭表达检查会误拒合理改写，创作空间有限；时长仅为 timing-v1 估算。

完整官方平台审核、开放域事实核验、会话恢复、HTTP API、前端、数据库和向量检索未实现，属于当前能力边界，不能直接列为原题必交缺口。个人材料与最终提交仍待完成，见 [复盘](05-retrospective.md)。

历史 run.json 摘要保持不改；当前 agent 提示词、main 元数据、profile 接入和 Mock 适配已变化，因此旧故障真实运行也不对应当前完整源码。旧版本结果按原始摘要解释。三个本地工具的计算与事实判定未放宽；当前资料由审阅后的 profile 注入，源码测试见上方 105 项日志。

## 独立连接诊断的结论

宿主 [GET 列表](../examples/network-validation/host-models-001/report.json) HTTP 200、0.169 秒且包含配置模型；[POST 探测](../examples/network-validation/host-chat-001/report.json) 为 URLError 包装的 60.065 秒超时，未取得 HTTP 状态。后者指向连接建立或发送阶段，具体 TCP/TLS/发送细因仍未知；不能归因为模型推理慢，也不能凭一次 GET 成功保证聊天稳定。执行环境的 DNS 失败不外推用户宿主。

独立脚本支持可选 GET、POST 与安全阶段计时，生产客户端和 Agent 未改；生产 JSON 请求头原本正确。诊断阶段的 [112 项](../examples/network-validation/unittest-001.txt)、[115 项](../examples/network-validation/unittest-002.txt) 日志属于历史版本，最新为 [119 项](../examples/network-validation/unittest-003.txt)。诊断测试使用模拟传输，不是额外真实业务成功案例。详见 [网络记录](../examples/network-validation/README.md)，无需继续诊断才能整理或提交现有材料。
