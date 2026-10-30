# 短视频脚本 Agent

基于 Python、LangGraph 1.2.18 和 DeepSeek V4 Pro 的单 Agent。已实现六动作循环、三个本地工具、文件/终端输入、离线 Mock、版本检查和输出记录。真实正常任务与一次检索故障注入任务均已完成，最终分别为 v2 / 7.1 秒与 v2 / 9.4 秒。

当前验证了 79 项测试和最小产品事实场景；事实检查采用素材原文与封闭表达，存在明显误拒，不能代表通用事实判断或平台实际审核。

## 安装

已验证环境：Python 3.14.4，项目虚拟环境位于 `.venv/`。其他 Python 版本未在本项目实际验证。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
```

`requirements.txt` 固定直接依赖，`requirements.lock.txt` 保存此次安装的全部 39 个依赖版本。DeepSeek HTTP 接入使用标准库，不依赖 OpenAI SDK 或完整 LangChain Agent。LangGraph 负责状态图和条件路由。

## 模型配置

首次克隆时复制 [.env.example](.env.example) 为本地 `.env`，已有配置保留：

```bash
cp -n .env.example .env
```

仅在本地填写 `DEEPSEEK_API_KEY`。默认模型 `deepseek-v4-pro`，API 地址 `https://api.deepseek.com`，单次超时 60 秒。进程环境优先于本地文件。Mock 模式不读取密钥，也不调用模型。

DeepSeek 默认直连，`DEEPSEEK_USE_PROXY=false`；需要继承系统代理时设为 `true`。该选项仅影响此客户端，不修改 pip 或全局代理。用户在本机直连后完成真实验证；本执行环境曾因 DNS 失败无法连接，相关失败记录保留。

## 运行 CLI

```bash
# 离线：Mock 模型调用真实本地工具
.venv/bin/python -m src.main --mode mock --input examples/normal/input.json

# 真实模型
.venv/bin/python -m src.main --mode real --input examples/normal/input.json

# 终端粘贴多行 JSON，以单独一行 END 提交
.venv/bin/python -m src.main --mode mock --interactive

# 验证超时长后的修订（Mock，不证明真实模型效果）
.venv/bin/python -m src.main --mode mock --input examples/normal/input.json --mock-scenario over-duration
```

默认输出到 `outputs/<run_id>/`，也可用 `--output-dir` 指定新目录；程序拒绝覆盖已有目录。一次输入对应一次任务，缺信息时输出问题并结束，首版不恢复会话。

输出包含 `result.json`、`script.md`、`checks.json`、`history.json`、`trace.jsonl` 和 `run.json`。历史保留各版草稿和检查；最终结果只能使用当前稿对应的检查。退出码：0 完成，1 需补充或未完成，2 执行失败。

其他测试参数：`--max-steps`（默认 12）、`--max-tool-calls`（默认 8）、`--max-transport-retries`（默认 1）；`--simulate-search-failure` 明确注入一次工具故障。模型请求重试计入步骤预算。

## 测试和评审入口

```bash
.venv/bin/python -m unittest discover -s tests -v
```

79 项测试全部通过，无跳过项。HTTP 单元测试使用模拟响应，Mock 集成使用真实 LangGraph 和本地工具；真实模型效果另以实际 Trace 验证。

- [需求和验收映射](docs/01-requirements.md)
- [实现方案](docs/02-solution.md)
- [评估、失败和限制](docs/03-evaluation.md)
- [AI 使用与个人贡献](docs/04-ai-usage.md)
- [复盘](docs/05-retrospective.md)
- [数据约定](docs/06-data-contracts.md)
- [工具能力边界](docs/07-tools.md)
- [Agent 协议与状态](docs/08-agent-loop.md)
- [真实/Mock 执行记录](examples/agent-validation/README.md)

## 最小资料与独立工具

[materials.json](data/materials.json) 仅含 P01“支持为视频添加字幕”；[brand_rules.json](data/brand_rules.json) 仅含不得虚构功能或效果数据。它们是用户指定的合成测试资料，不归属于真实品牌；“通用短视频”不是平台官方规则。

```bash
.venv/bin/python -m src.tools search --query 字幕 --material-ids P01
.venv/bin/python -m src.tools estimate --script examples/tool-validation/input-script.json --target-seconds 30
.venv/bin/python -m src.tools check --script examples/tool-validation/input-script.json
```

## 目录与提交状态

`src/` 包含 CLI、数据结构、模型、Agent、工具和 Trace；`tests/` 为可执行测试；`data/` 为素材、规则和[官方来源登记](data/sources.md)；`examples/` 为输入及实际证据；`docs/` 为说明。协作规则见 [AGENTS.md](AGENTS.md)。

`.env`、`.venv/`、`note/`、`outputs/` 不纳入 Git，运行与评审不依赖本地笔记。官方规则与更丰富产品资料尚未转为数据集，未实现前端、HTTP API、会话恢复或视频生成。

题目：短视频脚本 Agent，题号待用户补充。仓库为 [Universeping/agent-campus-submission-example](https://github.com/Universeping/agent-campus-submission-example)。实际用时待候选人填写；最终提交 SHA 用 `git rev-parse HEAD` 获取，不追写自身所在提交的 SHA。
