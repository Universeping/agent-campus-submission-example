# 本地工具阶段历史验证

这里的脚本都是人工编写的合成测试输入，不是模型输出，也不是 `normal` 场景的 Agent 执行结果。本目录记录工具阶段的历史状态，当前项目结论见 [效果验证](../../docs/03-evaluation.md)。

| 输入或记录 | 用途 |
| --- | --- |
| [input-script.json](input-script.json) | 单事实和允许表达组成的手工脚本。 |
| [unsupported-script.json](unsupported-script.json) | 引用 P01 但声称效率提升 80%，验证引用存在不代表事实有依据。 |
| [overlong-script.json](overlong-script.json) | 重复事实句构造超时长输入，不代表推荐的实际脚本。 |
| [unittest-001.txt](unittest-001.txt) | 工具阶段当时 37 项契约与工具测试的实际输出，含文件指纹；不是当前全量测试数量。 |
| [run-manifest.json](run-manifest.json) | 七次实际命令、退出码、输出文件及指纹，明确没有模型或 Agent 运行。 |

## 实际工具结果

| 场景 | 输出 | 实际结果 |
| --- | --- | --- |
| 检索字幕 | [search-result.json](search-result.json) | 返回 P01 与原文，退出码 0。 |
| 检索翻译 | [empty-search-result.json](empty-search-result.json) | 空结果且无工具错误，退出码 0。 |
| 手工脚本估时 | [duration-result.json](duration-result.json) | 5.35 秒，30 秒上限下通过，退出码 0。 |
| 手工脚本规则检查 | [rule-result.json](rule-result.json) | 通过，版本与指纹对应输入，退出码 0。 |
| P01 引用下编造效果 | [unsupported-rule-result.json](unsupported-rule-result.json) | 不通过，定位至 S02，退出码 1。 |
| 超时长输入 | [overlong-duration-result.json](overlong-duration-result.json) | 34.5 秒，超过 30 秒，退出码 1。 |
| 素材文件不可读 | [missing-material-result.json](missing-material-result.json) | `data_unavailable`，退出码 2；缺失路径为故意设置的测试输入。 |

复现命令见 manifest；估时假设和检查边界见 [工具说明](../../docs/07-tools.md)。本阶段没有模型修订前后效果的证据，也未完成三类 Agent 场景或两条模型路径要求。
