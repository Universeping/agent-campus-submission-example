# 资料评估与 profile 验证证据

实际环境 Python 3.14.4、LangGraph 1.2.18、python-dotenv 1.2.4。源代码、测试与审阅配置摘要见 [105 项测试日志](unittest-001.txt)，全部通过，无跳过。数据评估与接入方式见 [说明](../../docs/09-data-pack.md)。

## 原始包与审阅

- [原始包工具兼容报告](raw-pack-report.json)、[摘要](raw-pack-summary.txt)：实际复跑 140 项检查，全部通过；报告由 /tmp/agent-campus-pack-review-001 原样复制。验证脚本只写仓库外报告，无模型调用。
- [资料审阅](pack-review.json)：40 条原始事实、39 条启用、1 条隔离、8 组配置和 20 条项目规则；原包 62 个内容摘要全部匹配。
- [文件与工具复核](verification.json)：当前测试摘要、原包摘要、八条实际输出与 Trace、来源映射、本地工具重算、链接和凭据过滤均已核对；没有模型调用。
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

[real-capcut-web-001](real-capcut-web-001/result.json) 为当前环境执行的真实模式尝试，最终 connection_error，未收到模型动作；[Trace](real-capcut-web-001/trace.jsonl) 保留失败。没有新的真实 profile 成功结论，也不能把旧 P01 真实路径挪作本轮证明。

在可连接 DeepSeek 的宿主终端复跑，自动写入新的 outputs 目录：

```bash
.venv/bin/python -m src.main --profile capcut_web_captions --mode real
.venv/bin/python -m src.main --profile bcut_ios --mode real
```

## 测试与历史证据

新 18 项配置测试覆盖全部启用事实和原始人工样例、产品/客户端及 Canva 模式隔离、来源一致性、隔离条目、必需规则、实际图循环和 CLI 导出。原始包 140 项不与项目 105 项相加为“模型测试数”。

此前 [提示词验证](../prompt-validation/README.md) 和 [初版 Agent](../agent-validation/README.md) 为历史代码与配置；各自原始文件不改。当前测试指纹以本目录日志为准。
