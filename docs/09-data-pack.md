# 产品资料包评估与接入

评估日期：2026-10-31。原始资料位于 data/data_pack/short_video_data_pack，保持用户提供的文件内容和清单摘要不变。审阅决策在 [pack_review.json](../data/pack_review.json)，加载器在 [profiles.py](../src/profiles.py)。

## 评估结论

原包 40 条事实、4 个产品、8 个独立 profile、12 条通用规则和 8 条范围规则，来源元数据通过 ID 与 id/fact 运行文件关联。它适合在现有工具基础上扩大业务测试。当前启用 39 条事实，保留 1 条待澄清；8 个配置均可运行，每次加载其中 14 或 15 条适用规则。

原包自带的验证脚本已在本仓库复跑：[140 项检查通过](../examples/data-validation/raw-pack-report.json)。这些检查包括人工脚本、逐条原文和禁用词，以及“混合总表缺少产品隔离”这个已知限制；不等于已经证明业务或模型效果。原包 62 个文件与其 file_hashes.json 全部匹配。

资料接入阶段完成 [105 项业务测试](../examples/data-validation/unittest-001.txt) 和 [8 次 Mock CLI 运行](../examples/data-validation/mock-runs.json)；后续另增 14 项独立诊断测试，最新 [119 项日志](../examples/network-validation/unittest-003.txt) 全部通过。Mock 实际使用 LangGraph 和本地工具，但不证明真实模型会正确选择事实。较早执行环境的真实尝试 connection_error，见 [失败结果](../examples/data-validation/real-capcut-web-001/result.json)。随后宿主完成 [CapCut 网页端](../examples/data-validation/real-capcut-web-002/result.json) v1 / 21.4 秒和 [必剪 iOS](../examples/data-validation/real-bcut-ios-001/result.json) v1 / 13 秒；[P01 批量](../examples/data-validation/real-baseline-batch-001/report.json) 首例连接失败后，工具失败、空资料和无关资料已通过独立复跑补齐，见 [当前索引](../examples/data-validation/README.md)。

## 来源与含义

资料库的 fact 是受控中文转述，不是官方网页逐字引文。原文匹配工具核对的是本地 fact。源链接、定位、日期、条件和客户端范围通过 sidecar 保留，不能用产品文档推断价格、账号权益、地区可用性或准确率。

| 来源 | 本轮复核与边界 |
| --- | --- |
| [CapCut 字幕](https://www.capcut.com/resource/how-to-add-subtitle-in-capcut) | 官方搜索返回的同页正文包含 Web 与 Desktop 分步说明；初次直接读取失败，不能写成直接网页全部成功。 |
| [CapCut 文字转语音](https://www.capcut.com/tools/text-to-speech?enter_from=page_footer) | 通过带查询参数的官方页读取线上编辑流程及语速/音量说明，不纳入页面价格或效果宣传。 |
| [Canva 可编辑字幕](https://www.canva.com/help/generate-edit-captions-on-videos/) | 文字/时间轴、样式、导出与适用条件，应保持 editable_captions 范围。 |
| [Canva 仅查看字幕](https://www.canva.com/help/enable-captions/) | 官方明确它与可编辑字幕是不同功能；不能编辑/下载不代表所有 Canva 字幕都受此限制。 |
| [Adobe 字幕](https://helpx.adobe.com/express/web/video-creation-and-editing/edit-videos/caption-video.html) | 编辑器与 Caption video 快捷操作分别保留，不扩展到移动端。 |
| [Adobe 裁短](https://helpx.adobe.com/express/web/video-creation-and-editing/edit-videos/trim-videos.html)、[调整尺寸](https://helpx.adobe.com/express/web/video-creation-and-editing/edit-videos/resize-videos.html) | Trim 改时长，Resize 改尺寸，不将两者混为同一功能。 |
| [必剪 App Store 开发者说明](https://apps.apple.com/cn/app/id1299589486) | 使用开发者功能列表，限定 iOS；不依据用户评论、评分或免费标签推断功能权益。 |

逐来源方法和限制见 [pack-review.json](../examples/data-validation/pack-review.json)。这是文档依据核对，没有实际操作产品或验证账号权限。

P_CAN_010 的“Canva 网站目前不支持视频字幕”容易把 Canva websites 与整个网页编辑器混淆。源页面确有网站限制，但需先明确中文适用对象；原条目保留，当前通过审阅配置排除，而不凭模型猜测改写。仅查看配置仍可用 P_CAN_008/009 两条事实。

全部 20 条规则是项目自定演示政策，不是厂商品牌手册或抖音官方规则。B01 使用既有事实检查，其他规则只检查 forbidden_terms。它们会漏掉词表外变体，也可能误拒包含禁词的合理否定句；不宣称具备语义审核能力。

## 接入方式

```bash
.venv/bin/python -m src.main --list-profiles
.venv/bin/python -m src.main --profile capcut_web_captions --mode mock
.venv/bin/python -m src.main --profile bcut_ios --mode real
```

省略 --input 时使用配置自带的五字段需求；也可提供 --input 或 --interactive。输入的 platform 表示视频发布平台，profile 的 surface 表示产品客户端，两者不能混用。

profile 不能与 --materials/--brand-rules 混用。加载器校验分表与总表/清单一致，核对事实文字、产品、客户端、来源和审阅排除项，并强制保留全部适用规则。总表不是单产品任务的默认资料。原 P01/B01 最小案例继续作为独立基线保留。

模型上下文获得可信 data_scope。素材正文和来源元数据仅在真实检索后进入观察及状态，不在检索前把完整库内容当成已检索事实。产品范围由配置选择，程序不从自由文本猜测产品，也不交由模型放宽。

没有选择 profile 而手工传入混合总表时，旧的通用接口仍不具备产品隔离；本接入不声称任意外部 JSON 都经过了审阅。跨产品比较暂不支持这些单产品规则。

## 输出与可追溯性

profile 模式新增 sources.json，仅列实际稿件引用的素材及来源元数据；script.md 附来源链接、日期和适用端。run.json 保存 data_profile、选中/排除 ID、material_provenance，以及输入、审阅配置、资料/规则/元数据和源码摘要。TaskResult 仍使用来源 ID，详细来源通过 sources.json 对应，未更改 Material 的 id/fact 契约。

一次运行中的资料和规则固定。模型仍需保存稿件、执行两项检查，再申请完成；报告继续绑定版本和指纹。当前不跨配置恢复会话或复用旧报告。

## 当前能力边界

检索仍为关键词子串匹配，metadata.tags 尚未参与召回。事实检查仍只接受原文与原有封闭表达，没有因扩充事实而宣称支持任意改写。非字幕任务可用完整事实句作标题、使用既有通用画面，创作空间和受众/风格适配仍有限。2 个 profile 有真实正常成功，其他 6 个仅有 Mock CLI，不能宣称全部配置真实验证通过。数据库、向量召回未引入，也不是原题必需。

P01 工具失败、空资料、无关资料三例均通过；5 秒例有修订、重检及上限未完成退出，无最终修订成功证据，任务 incomplete、自定义评估 failed 保留。它们仍是合成基线，不外推到全部 profile。详情见 [真实分支复核](../examples/data-validation/real-branches-verification-001.json)，考核要求与自定义分类的区别见 [效果验证](03-evaluation.md)。
