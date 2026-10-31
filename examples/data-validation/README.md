# 资料评估与 profile 验证证据

实际环境 Python 3.14.4、LangGraph 1.2.18、python-dotenv 1.2.4。资料接入阶段的 [105 项业务测试日志](unittest-001.txt) 保留源码、测试与审阅配置摘要；最新 [119 项日志](../network-validation/unittest-003.txt) 全部通过，无跳过，另含 14 项独立诊断测试，不是 119 次真实模型验证。当前效果结论见 [评估](../../docs/03-evaluation.md)，数据接入方式见 [说明](../../docs/09-data-pack.md)。

## 原始包与审阅

- [原始包工具兼容报告](raw-pack-report.json)、[摘要](raw-pack-summary.txt)：实际复跑 140 项检查，全部通过；报告由 /tmp/agent-campus-pack-review-001 原样复制。验证脚本只写仓库外报告，无模型调用。
- [资料审阅](pack-review.json)：40 条原始事实、39 条启用、1 条隔离、8 组配置和 20 条项目规则；原包 62 个内容摘要全部匹配。
- [文件与工具复核](verification.json)：资料接入阶段的测试摘要、原包摘要、八条 Mock 实际输出与 Trace、来源映射、本地工具重算、链接和凭据过滤均已核对；没有模型调用。
- [原始人工样例](../../data/data_pack/short_video_data_pack/examples/) 属于工具输入，不是模型生成或修改的脚本。

## 八条 Mock 集成

每个目录由实际 CLI 生成 result/checks/script/history/trace/run 和 profile 专用 sources.json；[清单](mock-runs.json) 记录命令、状态和计数。

| profile | 事实/规则数 | 实际结果 | 证据 |
| --- | --- | --- | --- |
| capcut_web_captions | 3 / 14 | completed，5.4 秒 | [结果](mock-capcut_web_captions-001/result.json)、[Trace](mock-capcut_web_captions-001/trace.jsonl) |
| capcut_desktop_captions | 3 / 14 | completed，6.15 秒 | [结果](mock-capcut_desktop_captions-001/result.json)、[Trace](mock-capcut_desktop_captions-001/trace.jsonl) |
| capcut_web_voiceover | 4 / 14 | completed，5.65 秒 | [结果](mock-capcut_web_voiceover-001/result.json)、[来源](mock-capcut_web_voiceover-001/sources.json) |
| canva_web_editable | 7 / 14 | completed，7.4 秒 | [结果](mock-canva_web_editable-001/result.json)、[Trace](mock-canva_web_editable-001/trace.jsonl) |
| canva_web_view_only | 2 / 15 | completed，4.65 秒 | [结果](mock-canva_web_view_only-001/result.json)、[Trace](mock-canva_web_view_only-001/trace.jsonl) |
| adobe_web_captions | 5 / 14 | completed，7.9 秒 | [结果](mock-adobe_web_captions-001/result.json)、[Trace](mock-adobe_web_captions-001/trace.jsonl) |
| adobe_web_editing | 5 / 14 | completed，10.65 秒 | [结果](mock-adobe_web_editing-001/result.json)、[Trace](mock-adobe_web_editing-001/trace.jsonl) |
| bcut_ios | 10 / 14 | completed，3.65 秒 | [结果](mock-bcut_ios-001/result.json)、[来源](mock-bcut_ios-001/sources.json) |

Mock 在受限范围检索后使用首条事实、调用真实工具，仅证明执行和资料隔离可用；不证明真实模型会选择最相关事实、覆盖整个主题或写出合适风格。非字幕标题使用完整受支持事实，不借此宣称已经扩大创意表达能力。

## 真实尝试

[real-capcut-web-001](real-capcut-web-001/result.json) 为执行环境较早的真实模式尝试，最终 connection_error，未收到模型动作；[Trace](real-capcut-web-001/trace.jsonl) 保留失败。随后用户在宿主终端完成下面两条实际产品路径，原文件逐字节归档，源代码与资料摘要和当前版本一致。

| 归档目录 | 实际结果 | 过程与边界 |
| --- | --- | --- |
| [real-capcut-web-002](real-capcut-web-002/result.json) | completed，v1，21.4 秒，8 轮/3 次工具 | 引用 P_CAP_001/002/003；[Trace](real-capcut-web-002/trace.jsonl) 有一次 multiple_actions 拒绝、两次间歇连接错误，程序重试后继续。 |
| [real-bcut-ios-001](real-bcut-ios-001/result.json) | completed，v1，13 秒，6 轮/3 次工具 | 引用 P_BCT_001/002，覆盖字幕和文本朗读；[Trace](real-bcut-ios-001/trace.jsonl) 有一次 multiple_actions 拒绝后纠正。 |
| [real-baseline-batch-001](real-baseline-batch-001/report.json) | normal blocked，其余四例 not_run | 首例在两个约 60 秒的模型请求后报 connection_error，0 次业务工具；[Trace](real-baseline-batch-001/normal/trace.jsonl)。不是素材检索或规则检查失败。 |

[逐文件摘要与复核](real-host-verification-001.json) 保存原始 outputs 路径、归档位置和执行人。两个产品最终稿已用实际本地工具重新检查，报告、来源和指纹一致。它们均为首稿成功，不证明超时长修订；网络重试由程序执行，不包装为模型自主决策。当前日志无法进一步区分 DNS、TCP、TLS 或其他连接原因。

人工评阅：CapCut 使用了三条授权字幕事实；必剪旁白覆盖字幕与朗读，但标题仅称“字幕功能介绍”，衔接也较模板化，不能把 completed 解释为创作质量全面通过。两次正常成功与旧配置输入不同，不据此宣称新提示词降低了错误率。

若批量入口因首例连接错误停止，可逐个调用剩余案例，分别保存独立报告，某一例受阻不阻止其他独立命令：

```bash
for case_name in tool-failure no-materials unrelated-materials over-duration; do
  .venv/bin/python examples/prompt-validation/run_cases.py --mode real --case "$case_name"
done
```

它们仍使用 P01 合成基线。not_covered 表示没有触发目标分支，不能改记为通过；连接持续失败应保留受阻记录。

在可连接 DeepSeek 的宿主终端复跑，自动写入新的 outputs 目录：

```bash
.venv/bin/python -m src.main --profile capcut_web_captions --mode real
.venv/bin/python -m src.main --profile bcut_ios --mode real
```

## 宿主独立复跑的异常分支

原始报告、实际输出与 Trace 均逐字节复制，见 [摘要与复算](real-branches-verification-001.json)。与当前源码/资料摘要及原评估器判定一致：

| 案例 | 实际结果 | 证据 |
| --- | --- | --- |
| 工具失败 | passed，8 轮/5 次工具，v1 / 9.4 秒；注入失败后改查询，空结果后再缩短查询取得 P01，检查后完成 | [报告](real-baseline-tool-failure-001/report.json)、[Trace](real-baseline-tool-failure-001/tool-failure/trace.jsonl) |
| 空资料 | passed，needs_input，5 轮/4 次检索；实际空结果后请求资料，未生成脚本 | [报告](real-baseline-no-materials-001/report.json)、[Trace](real-baseline-no-materials-001/no-materials/trace.jsonl) |
| 无关资料 | passed，needs_input，4 轮/3 次检索；仅授权 P02，改查后仍为空，请求字幕事实 | [报告](real-baseline-unrelated-materials-001/report.json)、[Trace](real-baseline-unrelated-materials-001/unrelated-materials/trace.jsonl) |
| 5 秒超时长 | failed，任务 incomplete；v1 7.6 秒→v2 5.3 秒→v3 2.25 秒，但 v3 删除事实被 no_grounded_fact 拒绝；保存 v4 后第 12 轮连接错误，达到步骤上限，没有最终重检或 finish | [报告](real-baseline-over-duration-001/report.json)、[Trace](real-baseline-over-duration-001/over-duration/trace.jsonl)、[历史稿](real-baseline-over-duration-001/over-duration/history.json) |

补充 [缺输入运行](real-baseline-missing-input-001/result.json)：由 Codex 在当前代码实际执行 real 模式 CLI，缺 topic，needs_input，0 次模型调用；不是模型推断证据。

超时长任务状态为 incomplete，自定义评估 failed 保持不改。该评估要求最终重检完成或模型主动 finish(incomplete)，比原题允许修订或明确失败的字面要求更严格；不能直接把这个 failed 等同于考核整项不达标。现有记录展示了反馈修订、重检和上限未完成退出，但未证明最终修订成功或模型主动判断业务约束无法满足。详见 [判定边界](../../docs/03-evaluation.md)。

v4 虽恢复 P01 原文，但原任务没有该稿报告，不能用 v3 的时长通过或离线复算来证明完成。诊断性离线复算显示 v4 为 2.25 秒、规则通过，详情写在审阅摘要的 post_run_diagnostics，不混入原 Trace/报告。

用户已执行的扩大预算命令如下，全局默认仍为 12/8，实际结果见下文：

```bash
.venv/bin/python -m src.main --mode real --input examples/over-duration/input.json --max-steps 20 --max-tool-calls 10
```

该次 [20/10 预算复跑](real-baseline-over-duration-002/result.json) 在前两次模型请求均连接失败，每次约 60 秒，0 次工具/稿件；[复核](real-over-duration-retry-verification-001.json) 保留原文件摘要。此例未进入业务分支，无法判断增加预算的修订效果。后续 [独立连接诊断](../network-validation/README.md) 已记录列表成功与聊天超时；继续诊断或复跑不是当前材料收尾的前置条件。

空资料时允许范围已为空，模型仍检索了四次；超时长压缩曾删除唯一事实，且包含一次批量动作拒绝和一次连接错误。它们是后续效率与约束保持的改进点，不通过放宽事实检查或忽略预算来抹除。

## 测试与历史证据

新 18 项配置测试覆盖全部启用事实和原始人工样例、产品/客户端及 Canva 模式隔离、来源一致性、隔离条目、必需规则、实际图循环和 CLI 导出。原始包 140 项不与项目 105 项相加为“模型测试数”。

此前 [提示词验证](../prompt-validation/README.md) 和 [初版 Agent](../agent-validation/README.md) 为历史代码与配置，各自原始文件不改。本目录 105 项日志对应业务接入阶段，最新全量测试指纹见 [119 项日志](../network-validation/unittest-003.txt)。
