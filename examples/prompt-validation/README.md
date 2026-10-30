# 新提示词与业务分支验证

本轮更新 system prompt，不改变工具判定或完成条件。新运行的 run.json 保存 system_prompt_sha256；旧记录不追写。旧提示词的真实结果见 [历史运行索引](../agent-validation/README.md)。

## 一条命令运行

在仓库根目录执行，使用本地 .env 的 DeepSeek 配置：

```bash
.venv/bin/python examples/prompt-validation/run_cases.py --mode real
```

自动在 outputs/ 下创建唯一目录。report.json 汇总案例，子目录保存实际 CLI 的六类输出。不覆盖既有结果，不伪造动作或修改工具返回。若模型连接、超时或 HTTP 错误导致无法运行，记录 blocked，后续案例记为 not_run，避免重复请求不可用的服务。

只运行指定案例可重复传 --case：

```bash
.venv/bin/python examples/prompt-validation/run_cases.py --mode real --case no-materials --case unrelated-materials --case over-duration
```

离线检查使用 --mode mock。批量入口的退出码 0 表示所有选中案例的记录判定通过，1 表示存在失败、受阻或未覆盖。子 CLI 的 needs_input 退出码 1 在资料不足案例中是正常结果。

## 五个案例与判定

| 案例 | 输入/配置 | 验收 |
| --- | --- | --- |
| normal | [正常输入](../normal/input.json)、P01/B01 | completed，当前稿两项报告匹配，Trace 中先保存、后检查、再完成。 |
| tool-failure | 正常输入，显式注入一次 search 故障 | 收到错误后由模型重新选择检索，取得资料并完成；不是自动重试业务工具。 |
| no-materials | [需求](../no-materials/input.json)、[空资料](../no-materials/materials.json) | needs_input，给出问题，不生成产品脚本；允许直接根据空授权范围请求补充。 |
| unrelated-materials | [需求](../unrelated-materials/input.json)、[无关资料](../unrelated-materials/materials.json) | P02“支持调节音量”为本用例自定合成事实，与字幕需求无关；须实际检索得到空结果，再以 needs_input 请求补充。若直接请求，缺资料处理合理，但空检索分支记 not_covered。 |
| over-duration | [5 秒上限需求](../over-duration/input.json)、P01/B01 | 实际 estimate_duration 不通过后，模型修订并对新稿两项重检后完成，或主动 finish(incomplete) 给出理由。仅预算耗尽不算模型说明无法满足。 |

5 秒上限不保证首稿超时：若第一稿直接合格，报告为 not_covered，不能宣称验证了修订。真实运行不使用 --mock-scenario，也不人为改大时长或伪造失败。若自然生成持续无法覆盖，后续可独立设计明确标注人工首稿的修订评估入口；本轮尚未实现。

自动判定只核对 Trace 和结果中的结构条件。文案是否切合需求、引用是否实质支持、无法完成的理由是否合理，仍需阅读稿件和简短 reason。人工构造的分类器测试不是模型运行证据。

## 本轮实际结果

- [87 项测试日志](unittest-v2-001.txt)：全部通过，无跳过，包含当前源码/测试/批量入口摘要。
- [Mock 批量报告](mock-v2-001/report.json)：五例全部通过。超时长首稿 31.8 秒，修订为 2.65 秒，最终版本 2。Mock 不证明提示词效果。
- [真实尝试报告](real-v2-001/report.json)：normal 为 blocked，错误 connection_error，未收到模型动作；其余四例 not_run。因此本轮尚无新提示词的真实效果结论。
- [文件与工具复核](verification-v2-001.json)：核对当前测试指纹、新记录、历史草稿与本地工具结果、文档链接及凭据过滤；不调用模型。

真实尝试发生在批量分类器最终补充前，report.json 未包含后加的 runner_sha256；原始文件保留不改。Mock 报告与测试日志对应当前分类器。真实路径受阻后，先在宿主终端运行上面的命令，再检查 report 与原始 Trace。归档时使用新目录并如实保留未覆盖或失败结果。

与旧提示词比较时记录轮数、工具次数、multiple_actions 次数、事实/规则拒绝及最终结果；相同输入重跑也会有模型波动，不能仅凭一次成功宣称显著改善。
