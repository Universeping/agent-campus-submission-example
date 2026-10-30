# 短视频脚本 Agent：有来源的业务数据包

核验日期：**2026-10-31，Asia/Shanghai**。

本包提供 **40 条产品事实、12 条通用规则、8 条适用范围规则、8 组可单独加载的配置**。事实来自 8 个实际读到正文的官方产品说明或开发者产品描述。全部中文事实为必要的简短转述，保留来源 URL、页面定位、核验日期与适用范围。

已只读核对指定 WSL 仓库的 `Material`、`BrandRule`、加载器、检查器和 CLI。**没有修改该仓库，没有读取 `.env`，没有调用模型。** 当前验证范围仅为数据兼容性、检索、估时和规则检查，不是新增真实 Agent 运行证据。

## 先看哪些文件

| 文件 | 用途 |
| --- | --- |
| [CATALOG.md](CATALOG.md) | 阅读全部事实、规则与来源。 |
| [profiles/index.json](profiles/index.json) | 选择一个产品和客户端配置。 |
| `profiles/<名称>/materials.json` | 可直接传给现有 `--materials`。只有 `id/fact`。 |
| `profiles/<名称>/brand_rules.json` | 可直接传给现有 `--brand-rules`。只有 `id/rule/forbidden_terms`。 |
| `profiles/<名称>/input.json` | 与现有五字段 `TaskInput` 兼容的需求输入。 |
| [data/material_metadata.json](data/material_metadata.json) | 事实来源、适用端、功能范围、核验日期和关键词。**不传给现有加载器。** |
| [data/sources.json](data/sources.json) | 8 个来源的登记信息。 |
| [data/rule_metadata.json](data/rule_metadata.json) | 规则的项目自定属性、机制和边界。 |
| [verification/summary.txt](verification/summary.txt) | 实际验证摘要。 |
| [verification/report.json](verification/report.json) | 逐项结果、被读源码指纹和检查报告。 |
| [validate_against_repo.py](validate_against_repo.py) | 标准库验证脚本；只读指定仓库，报告写到仓库外。 |

现有 P01 是无真实品牌归属的合成事实。本包不重定义 P01，使用 `P_CAP_*`、`P_CAN_*`、`P_ADB_*`、`P_BCT_*`，避免把原来的合成资料当成官方事实。B01 保留原有规则文本，其余规则显式提供禁用词。

## 配置选择

| profile | 产品与端 | 事实数 | 适合的业务 |
| --- | --- | ---: | --- |
| `capcut_web_captions` | CapCut 网页端 | 3 | 自动字幕、校对、增删字幕行 |
| `capcut_desktop_captions` | CapCut 桌面端 | 3 | 识别语言、字幕时间与布局、导出 |
| `capcut_web_voiceover` | CapCut 网页端 | 4 | 文字转语音、声音选择、语速与音量 |
| `canva_web_editable` | Canva 网页端 | 7 | 可编辑字幕、样式、MP4 导出 |
| `canva_web_view_only` | Canva 网页端 | 3 | 仅查看字幕的编辑和下载限制 |
| `adobe_web_captions` | Adobe Express 网页端 | 5 | 生成、修改和排版字幕 |
| `adobe_web_editing` | Adobe Express 网页端 | 5 | 裁短视频与调整画面尺寸的区别 |
| `bcut_ios` | 必剪 iOS 版 | 10 | 字幕、朗读、提词、模板、画中画和投稿 |

**优先选择一个 profile，避免直接把 40 条总表全部注入同一次单产品任务。** 现有数据结构没有目标产品、客户端或功能范围字段。总表能被加载，但加载成功不代表跨产品隔离已实现；验证报告专门保留了这一已知边界。

范围规则用字面禁用项提供保守保护，它们也不是完整的语义范围验证器。若用户要做跨产品比较，不能直接使用这些单产品规则。

## 规则为什么能执行

现有实现只支持两种机制：

1. B01 的既有事实检查：素材引用存在、事实句与同镜引用的素材原文匹配、创意表达使用封闭列表等。
2. `forbidden_terms`：对标题、画面和旁白执行 Unicode NFKC、忽略大小写与空白后的字面匹配。

因此本包不添加 `max_title_length`、正则表达式或需要推理解释的新规则字段。B02–B12 的 `rule` 是可读说明，真正执行的是其 `forbidden_terms`。没有实现的自然语言规则不能被当成通过。

所有新增品牌/创作规则均为**项目自定的演示政策**，不是 CapCut、Canva、Adobe 或必剪官方品牌手册，也不代表抖音平台规则。标题字数、统一 30 秒、“前三秒”等没有被包装为平台规定。

例如 B02 只识别列出的数字表达，不意味着能靠该词表覆盖所有夸大宣传；其他无依据句子主要由严格原文检查阻断。原文检查拒绝合理改写时，应标为无法核验，不能声称发现了虚假事实。

## 对当前实现的适配限制

- 来源字段分离：现有 `Material(**item)` 不接受额外字段，所以运行文件保持 `id/fact`，详细来源通过素材 ID 查 sidecar 文件。
- “素材原文”指本地 `materials.json` 中的 `fact`，**不代表官方网页逐字引文**。
- 当前标题、画面、旁白衔接列表仍锁定于字幕题材。本包未修改它们。为使非字幕工具样例能通过，人工样例使用有依据的完整事实句作标题，画面使用既有允许表达“展示视频画面”。自然创作表达能力并未因此扩展。
- 没有针对现有 MockModel 的 P01 假设做适配；**不要假设换资料后所有 Mock 场景仍然成立**。
- 没有执行真实模型生成；所有 `examples/*/script.json` 都是人工构造的工具输入，不能当成模型输出或修订证据。
- 单镜和总时长由现有工具实际计算，样例检查结果见报告；不是实际配音测量。输入的 30 秒是用户目标，不是平台限制。
- 来源只保存简短转述、链接和定位，没有整页网页存档。官方页面以后可能变化；本包不能证明未来账号的功能权益或地区可用性。

## 可复制的使用方式

以下命令供你自行运行，本次没有执行真实模型。所有新结果写到当前会话的 `work/`，不写回代码仓库；`-B` 禁止生成仓库内的 Python 字节码缓存。真实模式会使用你自己的模型配置并产生模型调用。

在 WSL 中设置路径：

```bash
REPO=/home/yuchi/workspace/codex-notes/xiaoying/agent-campus-submission-example
PACK=/mnt/c/Users/Universe_ping/Documents/Codex/2026-10-30/b-w/outputs/short_video_data_pack
cd "$REPO"
```

先独立检索、检查人工样例：

```bash
.venv/bin/python -B -m src.tools search \
  --query 字幕 \
  --materials "$PACK/profiles/capcut_web_captions/materials.json"

.venv/bin/python -B -m src.tools check \
  --script "$PACK/examples/capcut_web_captions/script.json" \
  --materials "$PACK/profiles/capcut_web_captions/materials.json" \
  --brand-rules "$PACK/profiles/capcut_web_captions/brand_rules.json"

.venv/bin/python -B -m src.tools estimate \
  --script "$PACK/examples/capcut_web_captions/script.json" \
  --target-seconds 30
```

真实模型运行示例：

```bash
.venv/bin/python -B -m src.main --mode real \
  --input "$PACK/profiles/bcut_ios/input.json" \
  --materials "$PACK/profiles/bcut_ios/materials.json" \
  --brand-rules "$PACK/profiles/bcut_ios/brand_rules.json" \
  --output-dir "$PACK/../../work/bcut-real-001"
```

目录必须不存在；重跑时更换末尾的运行目录名。这些命令没有编辑仓库源文件，但真实运行需要读取仓库已有模型配置。

复跑本包确定性验证，无需模型、LangGraph 或密钥：

```bash
python3 -B "$PACK/validate_against_repo.py" \
  --repo "$REPO" \
  --report-dir "$PACK/../../work/data-verification-002"
```

验证脚本只读取 `schemas.py` 和 `tools.py` 并在内存中构造独立模块；不导入仓库的 `src/__init__.py`、模型接入或运行入口。另只读四个相关源文件/数据文件的指纹，报告目录禁止位于仓库内。

## 验证结果与下一步

本轮 **140 项检查通过，0 项失败**，包括 40 条事实逐条接受、8 个 profile 加载与样例检查、所有通用禁用词命中对应规则、错误引用、跨产品/端限制、空检索及合理改写误拒的边界。一个检查专门确认混合总表缺乏产品隔离，因此“通过”并不表示消除了该限制。四个读取文件的前后指纹一致。

下一阶段在选定 profile 下运行真实模型，保存正常、超时长修正、无素材和工具故障的实际 Trace；数据扩充和工具兼容检查不能代替这些验收证据。
