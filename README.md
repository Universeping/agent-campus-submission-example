# 短视频脚本 Agent

当前阶段：已建立业务理解基线 v0.1.0、最小资料、数据结构及三个独立本地工具，模型选用 DeepSeek V4 Pro。尚未实现 Agent CLI、模型循环、配置加载或 API 接入，没有真实模型执行记录或端到端业务验证结果。

## 提交信息

| 项目 | 内容 |
| --- | --- |
| 题号与业务任务 | 短视频脚本 Agent；题号待补充 |
| GitHub 所属账号及 URL | [Universeping/agent-campus-submission-example](https://github.com/Universeping/agent-campus-submission-example) |
| 仓库可见性 | 用户已确认创建；要求公开，当前环境尚未联网核验 |
| 最终 commit SHA | 提交前通过 `git rev-parse HEAD` 获取 |
| 实际用时 | 待记录 |
| 运行入口 | 三个工具 CLI 已可运行；支持文件/终端 JSON 输入的 Agent CLI 尚未实现 |
| 语言、模型、框架及版本 | Python；DeepSeek V4 Pro（`deepseek-v4-pro`）；拟用 LangGraph 小型状态图，框架及依赖版本待确认 |

## 环境、安装与运行

当前需要 Python 3.10 或更高版本。`src/schemas.py` 与 `src/tools.py` 已实现，其余模块仍为骨架，没有可运行的 Agent。`requirements.txt` 尚无第三方依赖；后续补充并锁定实际模型/框架依赖版本。

可运行全部 37 项数据契约与本地工具测试，无需 API 密钥或安装第三方依赖：

```bash
python3 -m unittest discover -s tests -v
```

测试验证数据约束与实际本地工具行为，不证明模型决策效果。[字段说明](docs/06-data-contracts.md)、[工具边界](docs/07-tools.md) 与 [实际结果](docs/03-evaluation.md) 分别维护。

三个工具可独立运行，示例脚本为人工输入：

```bash
python3 -m src.tools search --query 字幕 --material-ids P01
python3 -m src.tools estimate --script examples/tool-validation/input-script.json --target-seconds 30
python3 -m src.tools check --script examples/tool-validation/input-script.json
```

实际输出见 [工具验证](examples/tool-validation/README.md)，不是 Agent 的正常案例生成结果。

当前完成的是工具执行层。面向模型的工具名称、description、参数 JSON Schema，以及工具调用消息与结果反馈尚未实现；`schemas.py` 是程序内部数据约定，不等同于已向模型注册工具。因此当前尚无模型自主选择工具的能力。

计划采用 `python -m src.main` 作为入口，具体参数尚未定义；当前执行该模块不会生成脚本，不能作为功能验证。

### 模型配置准备

本地 `.env` 已加入 Git 忽略规则。本仓库提供 [.env.example](.env.example)，配置设计为：

```dotenv
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro
```

开发工作区已建立空密钥的 `.env`。其他克隆环境可将 `.env.example` 复制为 `.env`，仅在本地填写密钥。当前尚未实现文件加载或模型调用，填写后也不代表已接通 API；实现时计划优先使用进程环境变量，再读取本地文件。离线 Mock 计划无需真实密钥，其验证范围必须与真实模型验证分别说明。

模型标识和地址已按 [DeepSeek 官方文档](https://api-docs.deepseek.com/) 核对；工具调用协议见 [官方指南](https://api-docs.deepseek.com/guides/tool_calls/)。尚未进行真实 API 调用。

## 评审入口

1. [需求与成功标准](docs/01-requirements.md)
2. [方案与动态决策](docs/02-solution.md)
3. [验证结果与限制](docs/03-evaluation.md)
4. [AI 使用与个人贡献](docs/04-ai-usage.md)
5. [复盘与实际用时](docs/05-retrospective.md)
6. [输入、实际输出和执行记录](examples/README.md)
7. [输入、输出与工具结果的数据约定](docs/06-data-contracts.md)
8. [三个本地工具的行为与边界](docs/07-tools.md)

## 目录

```text
AGENTS.md          项目协作规则、文档更新时机和验证要求
src/
  __init__.py      Python 包
  main.py          CLI、输入校验、结果保存
  schemas.py       输入、素材、脚本、工具结果和任务状态
  model.py         真实模型接入与离线 Mock
  agent.py         决策循环、工具调度和执行上限
  tools.py         素材检索、估时、事实与品牌规则检查
  trace.py         执行记录
data/              官方来源登记、最小合成事实和品牌规则
tests/             数据契约与工具测试；Agent 测试待实现
examples/          输入、实际输出、Trace 与测试结果（待生成）
docs/              需求、方案、评估、AI 使用与复盘
requirements.txt   依赖清单（尚未引入第三方依赖）
.env.example       可提交的 DeepSeek 配置模板
```

开发协作遵循 [AGENTS.md](AGENTS.md)。本地可使用 `note/` 存放指定固化的讨论结果和个人参考文件，该目录已被 Git 忽略，不属于提交材料，也不是运行依赖。

## 首版范围

面向创作者，根据文本形式的主题、受众、平台、目标时长和风格，结合本地产品事实及品牌/平台规则生成可编辑脚本。资料将参考抖音、快手的官方规则与剪映、必剪的官方产品说明，同时使用明确标记的合成案例和自定创作配置。[来源登记](data/sources.md) 和最小合成资料已建立，官方来源数据集尚未生成，真实产品和平台组合待选定。

首版采用单 Agent 和三个本地工具：素材检索、时长估算、事实与品牌/平台规则检查，提供真实模型入口及明确标记的离线 Mock。检查结果绑定脚本版本，修改后重新检查；缺信息时输出补充问题并结束，暂不恢复会话。

计划在终端显示结果，同时保存 `result.json`、`script.md`、`checks.json` 和 `trace.jsonl` 至被 Git 忽略的 `outputs/<run_id>/`；选定的验收证据归档到 `examples/`。后续通过 HTTP API 复用同一 Agent 核心，再加前端字段表单。首版不实现视频生成、配音、HTTP API、网页编辑器或会话恢复。业务流程与待确认项见 [方案文档](docs/02-solution.md)。

## 第一条最小任务

- [产品事实](data/materials.json)：只有 P01“支持为视频添加字幕”。
- [品牌规则](data/brand_rules.json)：只有 B01“不得虚构功能或效果数据”。
- [用户需求](examples/normal/input.json)：面向新手、轻松风格，介绍字幕功能，总时长不超过 30 秒。

这些资料为合成测试夹具，不代表剪映、必剪或其他真实产品的事实与官方规则。平台使用“通用短视频”作为测试场景，不加载具体平台的官方规则。验收要求为输出完整、事实对应 P01、估时不超过 30 秒，且完成前最终版本通过估时和规则检查；详见 [正常案例验收](docs/03-evaluation.md#最小正常案例-normal)。当前仅准备好资料，尚未生成脚本、检查报告或 Trace。

## 提交前检查

- [ ] 选定题目，并将全部验收点映射到实现和验证材料。
- [ ] 实现模型选择动作、执行工具、观察结果、继续决策或结束的循环。
- [ ] 设置执行步数或工具调用次数上限，超限时明确返回未完成状态。
- [ ] 提供可复制的安装、运行与测试命令。
- [ ] 保存至少三组实际输入、输出和 Trace，覆盖正常、信息不足、工具失败。
- [ ] 展示至少两条由不同工具结果引发的模型执行路径。
- [ ] 在评估文档中引用实际证据，标明 Mock 边界、失败和未验证项。
- [ ] 完成 AI 使用、个人贡献、实际用时及未完成部分记录。
- [ ] 检查暂存文件不含真实密钥或隐私数据。
- [ ] 确认远程仓库公开，提交题号、GitHub URL 和最终 commit SHA。
