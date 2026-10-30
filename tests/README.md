# 可执行测试

使用项目虚拟环境：

```bash
.venv/bin/python -m unittest discover -s tests -v
```

当前共 79 项，全部通过，无跳过项。实际环境为 Python 3.14.4、LangGraph 1.2.18 和 python-dotenv 1.2.4；[当前日志](../examples/agent-validation/unittest-001.txt) 包含被测文件指纹。

| 文件 | 数量 | 覆盖范围 |
| --- | --- | --- |
| test_schemas.py | 15 | 数据契约、版本/内容绑定、完成约束、时长和引用结构。 |
| test_tools.py | 23 | 实际工具、估时边界、事实原文/受控表达、品牌禁用、加载及 CLI。 |
| test_model.py | 13 | 六动作声明、原生消息解析、无效与批量响应、HTTP 错误、配置及专用代理。 |
| test_agent.py | 24 | 节点边界、真实 LangGraph 路由、Mock+真实工具、修订重检、预算、失败及消息配对。 |
| test_cli_trace.py | 4 | CLI 文件/终端输入、输出、目录保护及 Trace 脱敏。 |

HTTP 单元测试使用假响应，Mock 模型按实际观察选择预设行为，二者均不证明真实模型效果。真实运行由用户在本机发起，代码与 Trace 已另行核对；见 [运行记录](../examples/agent-validation/README.md)。

早期 15 项和 37 项日志保留在 schema-validation、tool-validation 下，属于历史代码版本，不作为当前源码指纹依据。前端、会话恢复和真实模型多次重复的稳定性评估未覆盖。
