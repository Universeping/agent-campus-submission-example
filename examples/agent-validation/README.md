# Agent 执行与验证记录

环境 Python 3.14.4、LangGraph 1.2.18、python-dotenv 1.2.4。当前 [79 项测试日志](unittest-001.txt) 全部通过，无跳过。每个运行目录包含 result.json、checks.json、script.md、history.json、trace.jsonl、run.json，后者保存实际命令、配置边界和源码/资料摘要。

## 真实模型与入口校验

| 目录 | 输入与执行人 | 实际结果和证据 |
| --- | --- | --- |
| real-normal-002 | [正常输入](../normal/input.json)，用户在本机执行 | completed v2，7.1 秒，10 轮/6 次工具；[结果](real-normal-002/result.json)、[Trace](real-normal-002/trace.jsonl)、[历史](real-normal-002/history.json)。空检索后改查询，规则拒绝后修订并重检。 |
| real-tool-failure-001 | 同上，用户执行，显式注入一次 search 失败 | completed v2，9.4 秒，10 轮/6 次工具；[结果](real-tool-failure-001/result.json)、[Trace](real-tool-failure-001/trace.jsonl)、[历史](real-tool-failure-001/history.json)。错误后重新选择检索，补充事实句并重检。 |
| real-missing-input-001 | [缺 topic 输入](../insufficient-information/input.json)，Codex 执行 | needs_input；[结果](real-missing-input-001/result.json)、[Trace](real-missing-input-001/trace.jsonl)。real 模式入口校验，0 轮/0 工具，未调用模型。 |

真实任务使用 deepseek-v4-pro 非 thinking 模式。故障是 CLI 显式注入，恢复动作由模型选择。两次成功均出现过 multiple_actions 协议拒绝，模型纠正后继续。正常任务的原文匹配误拒属于检查器局限，不能称为发现虚假事实。

复现时使用新目录，保留既有证据：

```bash
.venv/bin/python -m src.main --mode real --input examples/normal/input.json --output-dir outputs/real-normal-review
.venv/bin/python -m src.main --mode real --input examples/normal/input.json --simulate-search-failure --output-dir outputs/real-failure-review
.venv/bin/python -m src.main --mode real --input examples/insufficient-information/input.json --output-dir outputs/real-missing-review
```

需要本地密钥。默认仅客户端直连，可用 DEEPSEEK_USE_PROXY=true 继承系统代理。模型输出可能不同，不应伪造相同 Trace。

## Mock 模型、真实图与工具

| 目录 | 预期与实际状态 | 证据 |
| --- | --- | --- |
| mock-normal-001 | completed v1 / 2.65 秒 | [结果](mock-normal-001/result.json)、[Trace](mock-normal-001/trace.jsonl) |
| mock-over-duration-001 | 31.8 秒失败→v2 / 2.65 秒通过 | [历史](mock-over-duration-001/history.json)、[Trace](mock-over-duration-001/trace.jsonl) |
| mock-unsupported-claim-001 | 无依据效果数据被拒，修订 v2 完成 | [历史](mock-unsupported-claim-001/history.json)、[Trace](mock-unsupported-claim-001/trace.jsonl) |
| mock-tool-failure-001 | 注入一次检索失败后恢复 | [结果](mock-tool-failure-001/result.json)、[Trace](mock-tool-failure-001/trace.jsonl) |
| mock-no-materials-001 | 空资料，needs_input | [空资料输入](../no-materials/materials.json)、[结果](mock-no-materials-001/result.json)、[Trace](mock-no-materials-001/trace.jsonl) |
| mock-missing-input-001 | 缺主题，needs_input，无模型步骤 | [结果](mock-missing-input-001/result.json)、[Trace](mock-missing-input-001/trace.jsonl) |
| mock-execution-limit-001 | 两轮预算耗尽，incomplete | [结果](mock-execution-limit-001/result.json)、[Trace](mock-execution-limit-001/trace.jsonl) |
| mock-early-finish-001 | 过早 finish 被拒，补检查后完成 | [结果](mock-early-finish-001/result.json)、[Trace](mock-early-finish-001/trace.jsonl) |

实际参数见各目录 run.json：将 command 的 python 换成 .venv/bin/python，output-dir 换成新路径即可重跑。缺输入、缺资料和预算结束的退出码为 1，属于预期。Mock 不证明真实模型决策或改稿能力；真实超时长修订尚待验证。

## 保留的连接失败

[real-normal-001](real-normal-001/result.json) 和 [real-tool-failure-local-001](real-tool-failure-local-001/result.json) 为 Codex 执行环境中的连接失败，最终 failed。未收到模型动作，后者也没有执行注入的工具故障；不计入真实业务路径。

## 版本与复核

原始记录保持不改。早期 Mock、real-normal-002 的 model/main 摘要与当前版本有代理配置等差异，不能写成全部来自当前源码；各自 run.json 保存实际摘要。最新单测、real-tool-failure-001 对应当前源码。

[verification.json](verification.json) 由读取实际文件、重算指纹、重新执行本地工具和核对 Trace 生成；[run-manifest.json](run-manifest.json) 汇总全部运行、命令和证据文件摘要。复核不会调用模型，也不把历史 Trace 改写为当前版本。更多失败分析见 [评估](../../docs/03-evaluation.md)。
