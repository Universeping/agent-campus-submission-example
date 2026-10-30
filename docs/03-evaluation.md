# 效果验证

状态：37 项数据契约及本地工具测试通过，已保存七次实际工具命令输出。尚未实现或运行 Agent，没有模型生成、动态决策或自主修订证据。

## 当前测试与工具结果

- 命令：`python3 -m unittest discover -s tests -v`。
- 实际结果：15 项契约测试与 22 项工具测试全部通过，退出码 0。
- 当前日志：[tool-validation/unittest-001.txt](../examples/tool-validation/unittest-001.txt)，包含被测代码与资料指纹。
- 工具测试：[test_tools.py](../tests/test_tools.py)，覆盖实际检索、估时、受控事实检查、品牌禁用、CLI、错误与报告版本。
- [工具执行清单](../examples/tool-validation/run-manifest.json) 记录七条实际命令及退出码；输入脚本均为人工合成，不是模型生成。

| 场景 | 实际结果 | 证据 |
| --- | --- | --- |
| 素材命中 | 返回 P01 原文 | [search-result.json](../examples/tool-validation/search-result.json) |
| 无匹配资料 | 空结果，无工具错误 | [empty-search-result.json](../examples/tool-validation/empty-search-result.json) |
| 手工脚本估时 | 5.35 秒，30 秒上限下通过 | [duration-result.json](../examples/tool-validation/duration-result.json) |
| 手工脚本检查 | 来源与受控表达通过 | [rule-result.json](../examples/tool-validation/rule-result.json) |
| P01 下编造效果 | 不通过，定位到 S02 | [unsupported-rule-result.json](../examples/tool-validation/unsupported-rule-result.json) |
| 超时长脚本 | 34.5 秒，不通过 | [overlong-duration-result.json](../examples/tool-validation/overlong-duration-result.json) |
| 素材文件不可读 | `data_unavailable`，退出码 2 | [missing-material-result.json](../examples/tool-validation/missing-material-result.json) |

估时假设与事实核验边界见 [工具文档](07-tools.md)。这些结果证明工具行为，不等同于三类 Agent 场景或两条真实模型路径通过。

## 历史数据契约测试

- 命令：`python3 -m unittest discover -s tests -p 'test_schemas.py' -v`。
- 实际结果：15 项测试全部通过，退出码 0。
- 测试代码：[test_schemas.py](../tests/test_schemas.py)。
- 实际日志：[unittest-001.txt](../examples/schema-validation/unittest-001.txt)，包含执行时间、Python 版本、基线提交和被测文件指纹。
- 重点：分别拒绝过期的估时与规则结果；内容变了但版本未变也拒绝；缺少检查、超时、擅自放宽上限、镜头覆盖错误和阻断规则问题均不能完成。
- 边界：报告是单元测试构造的数据，未执行真实估时、事实检查、离线模型或真实模型。没有将构造报告伪装成正常案例的实际结果。
- 此日志保存 schemas 初版的历史结果。当前 `BrandRule` 已增加可选禁用词字段，源码指纹以本页当前 37 项测试日志为准；原有 15 项契约测试也已在当前套件中通过。

## 待执行的验证

| 场景 | 预期 | 实际结果 | 证据 |
| --- | --- | --- | --- |
| 正常任务 | 单事实字幕脚本，输出完整、事实有依据、时长不超过 30 秒、最终版本检查通过 | 输入已准备，未运行 | [输入](../examples/normal/input.json)；实际输出与 Trace 待生成 |
| 信息或资料不足 | 补充查询、请求必要信息或明确说明不足 | 未运行 | 待生成 |
| 无可用素材 | 根据空检索结果改写查询或请求补充资料 | 未运行 | 待生成 |
| 工具失败 | 根据返回结果调整动作或明确返回未完成 | 未运行 | 待生成 |
| 首稿超时长 | 根据估时反馈修订并重新检查，或明确失败 | 未运行 | 待生成 |
| 无依据的产品表达 | 检出并修改，来源引用不能仅有 ID 存在性检查 | 未运行 | 待生成 |
| 执行上限 | 到达限制后明确返回未完成 | 未运行 | 待生成 |

实现后补充全部题目验收点的预期与实际结果。运行后引用 `examples/` 中的具体输入、输出、Trace 和测试结果文件，记录可复制的命令、环境和模型配置。

## 最小正常案例 normal

资料：[产品事实](../data/materials.json)、[品牌规则](../data/brand_rules.json)、[输入](../examples/normal/input.json)。P01 与 B01 是用户指定的合成测试事实和自定规则，无真实品牌归属。

| 验收项 | 预期 | 当前结果 |
| --- | --- | --- |
| 输出完整 | 标题、分镜、旁白、预计时长、来源、状态均存在且可用 | 未运行 |
| 事实有依据 | 产品功能表达能对应 P01，不增加未经支持的能力或效果数据 | 未运行 |
| 时长符合要求 | 最终估时工具结果不超过 30 秒，每镜与总时长可核对 | 未运行 |
| 完成前检查 | 最终版本经过估时及规则检查且通过，有同版本结果可追溯 | 未运行 |

已验证三份 JSON 与数据契约兼容，完成条件有单元测试覆盖；另有人工脚本的实际工具结果。正常案例仍未由模型执行，没有模型生成脚本或 Agent Trace，不将工具示例描述为正常案例通过。

## v0.1.0 验证准备

- 真实模型选用 `deepseek-v4-pro`，尚未调用，账户权限、额度和适配器兼容性均未验证。
- CLI 计划支持文件及终端 JSON 输入；缺信息后返回补充请求并结束，首版不测试跨次会话恢复。
- `outputs/` 为本地运行目录，验收证据需归档到 `examples/`，核对脚本、事实来源和检查结果对应同一版本。
- 来源登记仅证明完成资料调研，不证明已实现官方规则检测或产品能力验证。最小合成资料已准备，官方来源数据集尚未生成。
- 工具故障注入、真实估时触发的修订、调用上限和最终检查版本一致性将纳入测试；不能预设成功 Trace。

## 失败与限制

当前具备数据约定、完成条件校验、独立工具、单元测试和最小合成资料，没有可运行的 Agent 或端到端业务测试。规则/素材库和估时配置变化后的历史失效处理仍待运行器实现。事实核验为保守的原文和封闭表达检查，会误拒有效改写，不能覆盖任意自然语言或保证平台审核。离线 Mock 只验证流程；真实模型效果必须由真实调用证据支持。

除测试和独立工具运行外，执行文档本地链接、证据文件指纹和差异格式检查；未调用模型，不证明模型生成与修订效果。
