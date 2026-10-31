# 短视频脚本 Agent

基于 Python、LangGraph 1.2.18 和 DeepSeek V4 Pro 的单 Agent。已实现六动作循环、三个本地工具、文件/终端输入、离线 Mock、版本检查和输出记录。当前真实正常路径为 CapCut 网页端 v1 / 21.4 秒、必剪 iOS v1 / 13 秒；缺关键信息、工具失败、空资料、无关资料均有实际记录。5 秒超时长案例展示了修订与重检，最终达到上限返回 incomplete，尚无最终修订成功证据。

当前结论、历史记录及证据边界见 [效果验证](docs/03-evaluation.md)。

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

需要单独排查连接时，可在运行 Agent 的同一终端执行：

```bash
.venv/bin/python scripts/check_deepseek_connection.py
```

诊断复用模型配置和代理设置，仅查询模型列表，自动保存脱敏报告；可区分 DNS、TLS、超时和 HTTP 状态。它不请求聊天生成，也不证明后续生成连接稳定，详见 [说明](examples/network-validation/README.md)。

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

119 项测试全部通过，无跳过项。HTTP 单元测试使用模拟响应，Mock 集成使用真实 LangGraph 和本地工具；真实模型效果另以实际 Trace 验证。最新全量日志见 [连接诊断验证](examples/network-validation/README.md)，业务配置运行见 [资料验证](examples/data-validation/README.md)。

P01 基线的正常、故障、空资料、无关资料、超时长批量验证：

```bash
.venv/bin/python examples/prompt-validation/run_cases.py --mode real
```

自动新建 outputs/ 目录；首稿直接满足短时长时记为未覆盖修订，连接失败时记录受阻。入口及自定义判定见 [批量验证说明](examples/prompt-validation/README.md)，当前真实结果见 [运行索引](examples/data-validation/README.md)。超时长原报告 failed 保留：任务实际为 incomplete，有反馈修订及上限退出记录，不能称为最终修订成功，也不直接等同于考核不达标。

- [需求和验收映射](docs/01-requirements.md)
- [实现方案](docs/02-solution.md)
- [评估、失败和限制](docs/03-evaluation.md)
- [AI 使用与个人贡献](docs/04-ai-usage.md)
- [复盘](docs/05-retrospective.md)
- [数据约定](docs/06-data-contracts.md)
- [工具能力边界](docs/07-tools.md)
- [Agent 协议与状态](docs/08-agent-loop.md)
- [产品资料包评估与接入](docs/09-data-pack.md)
- [真实/Mock 执行记录](examples/agent-validation/README.md)

## 最小资料与独立工具

可按审阅后的配置使用实际产品资料，无需手动拼接素材和规则：

```bash
.venv/bin/python -m src.main --list-profiles
.venv/bin/python -m src.main --profile capcut_web_captions --mode mock
.venv/bin/python -m src.main --profile bcut_ios --mode real
```

--profile 默认采用对应输入样例，可用 --input 覆盖需求；不能再混用 --materials/--brand-rules。一次只加载当前产品与客户端资料和全部适用规则，保留来源日期及限制。profile 输出另含 sources.json，script.md 附来源链接，run.json 保存配置、元数据和摘要。P_CAN_010 因 Canva websites 的中文表述易混淆暂缓使用，详见 [评估](docs/09-data-pack.md)。

[materials.json](data/materials.json) 仅含 P01“支持为视频添加字幕”；[brand_rules.json](data/brand_rules.json) 仅含不得虚构功能或效果数据。它们是用户指定的合成测试资料，不归属于真实品牌；“通用短视频”不是平台官方规则。

```bash
.venv/bin/python -m src.tools search --query 字幕 --material-ids P01
.venv/bin/python -m src.tools estimate --script examples/tool-validation/input-script.json --target-seconds 30
.venv/bin/python -m src.tools check --script examples/tool-validation/input-script.json
```

## 目录与提交状态

`src/` 包含 CLI、数据结构、模型、Agent、工具、profile 加载和 Trace；`tests/` 为可执行测试；`data/` 为素材、规则、原始资料包、审阅配置和[来源登记](data/sources.md)；`examples/` 为输入及实际证据；`docs/` 为说明。协作规则见 [AGENTS.md](AGENTS.md)。

`.env`、`.venv/`、`note/`、`outputs/` 不纳入 Git，运行与评审不依赖本地笔记。产品资料已按 profile 接入；官方发布平台审核规则仍未实现，未实现前端、HTTP API、会话恢复或视频生成。

题目：短视频脚本 Agent，题号待用户补充。仓库为 [Universeping/agent-campus-submission-example](https://github.com/Universeping/agent-campus-submission-example)。实际用时待候选人填写；最终提交 SHA 用 `git rev-parse HEAD` 获取，不追写自身所在提交的 SHA。

可选连接诊断支持 `--chat` 和 `--timeout`，详见 [网络验证](examples/network-validation/README.md)。宿主已有列表成功和聊天超时记录，具体网络原因未确定；无需把继续诊断作为材料收尾的前置条件。
