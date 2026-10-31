# 官方来源登记 v0.1.0

核对日期：2026-10-30。此文件记录资料调研，不是已实现规则、最终数据集或模型验证报告。仅保存简短转述和定位，未复制整页内容。后续选用资料时应保留来源 ID，并复核版本、终端和适用范围。

2026-10-31 补充：用户资料包的 8 个官方/开发者来源已登记于 [sources.json](data_pack/short_video_data_pack/data/sources.json)，本轮读取与索引复核方法见 [pack-review.json](../examples/data-validation/pack-review.json)。8 个 profile 当前启用 39 条受控中文转述，P_CAN_010 暂缓；来源日期为包内核验记录，不意味着运行时联网核验或实测产品。接入和边界见 [说明](../docs/09-data-pack.md)。规则仍为项目自定演示政策，不冒充厂商官方政策。

## 模型与编排

| ID | 官方来源 | 本轮核对结果 |
| --- | --- | --- |
| DS-API-01 | [DeepSeek 首次调用](https://api-docs.deepseek.com/) | 已读取；提供模型 `deepseek-v4-pro` 及兼容 API 的调用地址。用户已在本机完成历史与当前真实任务，实际结果及边界见 [效果验证](../docs/03-evaluation.md)。 |
| DS-TOOLS-01 | [DeepSeek Tool Calls](https://api-docs.deepseek.com/guides/tool_calls/) | 已读取；客户端执行工具，并将结果交回模型。已验证非 thinking 模式的原生函数调用；thinking 模式未实现。 |
| DS-CHAT-01 | [DeepSeek Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/) | 已读取；接口参数列出所选模型及工具消息格式。 |
| LG-OVERVIEW-01 | [LangGraph 概览](https://docs.langchain.com/oss/python/langgraph/overview) | 已读取；已安装并固定 1.2.18，使用 StateGraph 节点和条件路由，集成验证见评估文档。 |

## 发布平台规范

### DY-AGREEMENT-01：抖音用户服务协议

- [官方页面](https://www.douyin.com/draft/douyin_agreement/douyin_agreement_user.html)，已读取正文。
- 页面标注更新日期为 2026-02-13，生效日期为 2026-02-20；这属于该页面，不代表全部平台规则的版本。
- 可参考位置：4.2（8）涉及不实信息，4.3（1）涉及标题与内容严重不符，10.2 涉及作品权利来源。
- 项目需要另行定义可执行的检查方式；这些条款不提供统一的标题字数、语速或“前三秒”数值标准。

### KS-COMMUNITY-01：快手社区管理规范

- [官方页面](https://www1.kuaishou.com/norm?tab=community)，已读取正文，未确认独立发布日期。
- 可参考位置：第三章五（3）涉及未经授权使用作品；第三章六（8）涉及虚假或夸大宣传；第四章三（2）涉及标题与内容不符。
- 适用平台为快手。条款摘要不等于自动审核规则，最终仅选取首版可验证的检查子集。

## 产品事实候选

### JY-PRODUCT-01：剪映官网

- [官方页面](https://www.jianying.com/)，已读取产品介绍。
- 可核对的候选事实：页面介绍人像背景移除和人声/背景声分离能力。
- 页面未给出本项目可据以引用的量化提效或准确率结果；具体终端、版本、收费条件仍需选用时核对。
- 仅登记候选，不代表首版已选定剪映，也不是剪映官方品牌表达规范。

## 已定位但未完整核验的入口

- [抖音安全与信任中心](https://trust.douyin.com/)：已定位官方入口，本轮正文未完整读取。不得据此补写社区公约细则。
- [必剪官网](https://bcut.bilibili.cn/)：页面依赖 JavaScript，本轮未取得完整产品说明。
- [必剪官方产品介绍入口](https://member.bilibili.com/studio/annyroal/download_bcut)：搜索可定位，直接读取正文受限；尚不作为已完整核验的素材事实。

## 转化为项目资料的约定

区分官方规范、产品事实、自定品牌/创作配置和合成测试数据。没有依据的数值、价格、免费范围、效果提升或全平台适用结论不得补写。官方说明是来源，项目检查逻辑是有限实现，两者分别记录。暂不把短视频创作经验写成平台强制要求，也不宣称检查通过就能通过平台审核。
