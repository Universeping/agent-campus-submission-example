# 可执行测试

使用项目虚拟环境：

```bash
.venv/bin/python -m unittest discover -s tests -v
```

当前共 119 项，全部通过，无跳过项。实际环境为 Python 3.14.4、LangGraph 1.2.18 和 python-dotenv 1.2.4；[当前日志](../examples/network-validation/unittest-003.txt) 包含被测文件指纹。

| 文件 | 数量 | 覆盖范围 |
| --- | --- | --- |
| test_schemas.py | 15 | 数据契约、版本/内容绑定、完成约束、时长和引用结构。 |
| test_tools.py | 23 | 实际工具、估时边界、事实原文/受控表达、品牌禁用、加载及 CLI。 |
| test_model.py | 13 | 六动作声明、原生消息解析、无效与批量响应、HTTP 错误、配置及专用代理。 |
| test_agent.py | 24 | 节点边界、真实 LangGraph 路由、Mock+真实工具、修订重检、预算、失败及消息配对。 |
| test_cli_trace.py | 4 | CLI 文件/终端输入、输出、目录保护及 Trace 脱敏。 |
| test_validation_cases.py | 8 | 批量分类不混淆首稿通过与修订、预算停止与模型主动结束，拒绝旧检查及错误时序。 |
| test_profiles.py | 18 | 39 条启用事实、8 个人工样例、元数据/必需规则与隔离条目、跨产品/客户端和 Canva 模式、实际图循环及 CLI 来源导出。 |
| test_connection_diagnostic.py | 14 | 模拟模型列表、URLError 包装分类、HTTP/格式处理、代理复用与凭据过滤。 |

HTTP 单元测试使用假响应，分类器测试使用人工构造事件，Mock 模型按实际观察选择预设行为，均不证明真实模型效果。旧提示词真实运行由用户在本机发起，见 [历史运行记录](../examples/agent-validation/README.md)；当前 CapCut/必剪两条真实正常路径、缺信息、P01 工具失败及两类资料不足均有记录。超时长有反馈修订、重检及明确未完成退出，无最终修订成功证据；自定义评估 failed 保留，含义见 [效果验证](../docs/03-evaluation.md) 和 [当前记录](../examples/data-validation/README.md)。原包另有 140 项兼容检查，不能与项目单测相加称为模型评估。

早期 15、37、79、87 项日志保留在 schema-validation、tool-validation、agent-validation、prompt-validation 下，属于历史代码版本，不作为当前源码指纹依据。前端、会话恢复和真实模型多次重复的稳定性评估未覆盖。

资料接入阶段的 [105 项日志](../examples/data-validation/unittest-001.txt) 保留，业务源码未变；新增独立诊断脚本不改变旧 Trace 或模型决策结论。

新增 POST 探测测试核对生产 JSON 请求头、单条诊断动作、HTTP/协议返回与包装异常分类，使用模拟传输，不证明真实宿主聊天可用。

阶段计时测试另外验证默认 TLS 校验及 connect/TLS/send/wait 的错误位置；模拟连接结果不作为真实宿主网络原因。
