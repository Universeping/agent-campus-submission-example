# 数据交换约定

实现位置：[src/schemas.py](../src/schemas.py)。使用 Python 标准库 `dataclasses`，无新增第三方依赖。数据对象不可变，传入的列表转为 tuple；`to_dict()` 输出 JSON 兼容字典，tuple 转为数组。需要 Python 3.10 或更高版本。

schemas 仅实现结构和一致性校验，不执行估时或规则判断。真实本地工具及脚本 JSON 加载器已在 `src/tools.py` 实现，见 [工具说明](07-tools.md)；Agent 和模型调用仍未实现。TaskInput、Material、BrandRule 可直接用现有 JSON 字段构造，派生字段只用于输出，不作为构造参数。

这些 Python 类型不是已注册到模型的工具参数 JSON Schema。工具 description、模型动作结构、参数适配和调用结果消息协议尚未实现。

## 字段清单

| 类型 | 字段及含义 |
| --- | --- |
| `TaskInput` | `topic`、`audience`、`platform`、`target_duration_seconds`、`style`；均必填，时长为有限正数。 |
| `Material` | `id`、`fact`，对应现有 P01 文件。 |
| `BrandRule` | `id`、`rule`，对应现有 B01 文件；可选 `forbidden_terms`，默认空，显式配置禁用表达。 |
| `Shot` | `id`、`visual`、`narration`、`source_ids`；镜头 ID 稳定，来源列表可空以表示创意衔接。 |
| `Script` | `version`、`title`、`shots`；派生 `source_ids` 和 `fingerprint`，来源由分镜汇总去重。版本从 1 开始。 |
| `ShotDuration` | `shot_id`、`duration_seconds`；将每镜估时关联到具体镜头。 |
| `DurationResult` | `script_version`、`script_fingerprint`、`shot_durations`、`target_duration_seconds`、`method`；派生总时长 `total_duration_seconds` 与 `passed`。 |
| `RuleIssue` | `rule_id`、`code`、`message`、可选 `shot_id`；全局或标题问题可不指定分镜。当前问题均视为阻断项。 |
| `RuleCheckResult` | `script_version`、`script_fingerprint`、`checked_rule_ids`、`issues`；检查规则列表不能为空，`passed` 由问题列表是否为空决定。 |
| `ToolError` | `tool`、`code`、`message`、`retryable`；区分工具运行失败和检查未通过。 |
| `SearchResult` | `query`、`materials`、可选 `error`；空结果且无错误代表未检索到，出现错误时不同时携带素材。 |
| `TaskResult` | `run_id`、`mode`、`status`、可选 `task_input` / `script` / 两类检查结果，以及 `risks`、`reason`、`missing_fields`、`errors`。 |

`mode` 为 `real` 或 `mock`，表示运行模式，不代表真实模型效果已验证。

## 状态与完成条件

- `completed`：有输入、脚本、非空素材引用和两类通过的检查，检查对象与最终稿一致，无未解决错误或缺项。
- `needs_input`：需要用户补充信息，必须提供原因，可列出缺失字段。
- `incomplete`：例如达到调用上限或约束无法满足，必须提供原因，可保留当前草稿和相符的检查。
- `failed`：执行失败，必须提供原因，可携带结构化工具错误。

最终结果中的检查一旦提供，就必须与脚本版本和指纹匹配，即使任务未完成也不能把旧检查冒充最终稿的检查。历史稿检查应放在运行记录中。

成功结果还校验估时覆盖的镜头集合与脚本完全一致，规则问题引用有效镜头，估时使用的上限等于用户上限。总时长由每镜估时求和，通过标志由程序派生，不能单独传入 `passed=True`。

## 版本与内容绑定

1. `Script.version` 是稿次，后续运行器负责修订时递增。
2. `Script.fingerprint` 由程序对标题、分镜顺序、镜头 ID、画面、旁白和来源的规范化 JSON 计算 SHA-256；不包含版本，因为两者分别比较。
3. 两类检查都保存 `script_version` 和 `script_fingerprint`，`matches(script)` 同时核对两者。
4. 版本从 1 改为 2，即使正文相同，第一稿的检查也不能用于第二稿；正文改了但误用版本 1，内容指纹仍会发现过期。
5. `TaskResult` 拒绝用过期、缺失或未通过的检查标记完成。

数据对象本身不能证明工具真正执行过，指纹也不是执行签名。后续运行器必须使用工具实际产生的结果，禁止把模型自报的“检查通过”直接当作工具报告，也不能仅重写旧报告的版本号来代替重检。

当前绑定覆盖脚本内容、稿次和用户时长上限；规则库、素材库或估时配置变化后的失效机制仍需后续运行器处理。来源与受控表达由工具核对，不由 schemas 代替；开放域语义核验尚未实现。

## 验证

测试见 [test_schemas.py](../tests/test_schemas.py)。测试使用人工构造的报告验证契约，不是估时、规则引擎、离线模型或真实 Agent 的运行记录。实际结果见 [评估文档](03-evaluation.md)。
