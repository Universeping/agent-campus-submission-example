# Agent loop 与模型协议

实现：[model.py](../src/model.py)、[agent.py](../src/agent.py)、[main.py](../src/main.py)、[trace.py](../src/trace.py)。

## 每轮程序步骤

1. 检查步骤和工具预算，发送请求前计入一个步骤。
2. 组装静态 system prompt、CURRENT_STATE_JSON 和原生消息历史。
3. 调用模型，解析单个函数调用的 ID、名称与 JSON 参数。
4. 本地校验参数类型、必填项、额外字段、素材范围和当前稿版本。
5. 执行管理动作或真实工具，将结果写入运行状态。
6. 用相同 tool_call_id 将实际结果交回模型，并保存 Trace。
7. 结束或进入下一轮；不能由固定分支自动改写脚本来代替模型决策。

## 模型输入与动作

系统指导定义任务、六动作、事实边界、版本重检、结束条件和简短 reason。动态状态包含需求、规则、允许表达、已检索事实、当前稿、当前检查、剩余预算和最新观察。完整素材正文不在检索前泄露。

新提示词明确 allowed_expressions 的 titles/visuals/narration 字段、同分镜引用、至少一条产品事实、主题相关性、工具失败与空结果的区别、request_input 与 incomplete 的选择和步骤预留。提示词不能代替执行器校验，也未扩大原文检查能力。新 run.json 记录 system_prompt_sha256；旧 Trace 不追写新摘要。

函数声明使用 JSON Schema：对象禁止未声明字段，字符串非空，版本为正整数，脚本有完整分镜，request_input 有具体问题。六个动作的参数见 [方案](02-solution.md#六个动作)。原始素材、规则和时长上限由执行器注入，模型不能提供修改后的核验依据。

模型只产生草稿和动作，不产生权威版本、指纹、估时和检查通过标志。普通文本、截断响应、非法 JSON、重复参数键或批量动作均作为无效响应处理。批量调用不执行，逐个返回相应错误，维持消息协议一致。

## 稿件和报告

scripts、duration_results、rule_results 以版本为键。save_script 每次接受新稿后递增版本并计算内容指纹。历史报告可查看，完成只读取 current_version 的报告；指纹还防止改正文却误用版本号。

检查工具异常、返回类型不符、报告版本/指纹不符或放宽用户上限，都不能变为通过。检查同稿再次失败时，旧通过项从当前可用结果移除，原观察仍保留在 Trace。

finish(completed) 校验已检索来源、当前版本两类检查、适用规则和 TaskResult 的结构约束。拒绝原因交回模型；有效 incomplete 和 request_input 可以保留草稿与当前检查。仅终态结果写 TaskResult，运行中不假装 completed。

## 错误、预算与 Trace

默认步骤上限 12、工具上限 8、请求超时 60 秒、临时传输重试 1 次。HTTP 429/5xx、连接和超时可在剩余预算内重试；认证错误直接 failed。适配器不私自重试，避免 SDK/图/业务三层叠加。

Trace 记录 run_id、顺序、时间、步骤、动作、参数、调用 ID、稿次、实际观察、工具计数及短依据。重试、协议错误、拒绝完成和终态也有记录。过滤已知密钥、认证字段及 reasoning_content，不将原始 HTTP 错误正文直接写入输出。

当前默认非 thinking 模式。未来如启用 thinking，必须按 [DeepSeek 协议](https://api-docs.deepseek.com/guides/thinking_mode/) 保留并在内存回传所需字段，不能照搬到公开 Trace。当前未实现此模式或跨次会话恢复。

## 独立验证

105 项测试覆盖真实 LangGraph 条件路由、Mock+真实工具、版本失效、受控事实、预算、消息配对、协议错误、传输错误、配置、代理范围、CLI、Trace 及分支分类。HTTP 单测为模拟传输，分类器使用人工事件。新提示词真实连接受阻，结果见 [当前验证](../examples/data-validation/README.md)；旧真实效果见 [历史运行索引](../examples/agent-validation/README.md)。

LangGraph 1.2.18 负责状态图及执行，python-dotenv 1.2.4 负责 .env 读取；DeepSeek HTTP、动作验证、业务状态和检查逻辑由项目实现。未使用框架预制 Agent、持久化 checkpointer 或多 Agent。

## 资料范围与来源

可信 profile 选择单产品、客户端和功能范围，固定加载全部适用规则，data_scope 不由模型修改。完整事实及来源仍须通过实际 search 才进入 retrieved_materials/retrieved_material_metadata。run.json 保存配置、来源、审阅与源码摘要，sources.json 仅导出实际稿件引用的条目。P01 基线与 profile 独立；手工加载混合总表仍不自动具备产品范围校验。详见 [资料接入](09-data-pack.md)。
