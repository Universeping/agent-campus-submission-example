# DeepSeek 连接诊断

本目录仅记录可选网络诊断及其历史，不替代业务验收，也不是材料收尾的前置条件。宿主已有 GET 列表成功与 POST 聊天超时记录，具体网络原因仍未知。最新 [119 项日志](unittest-003.txt) 全部通过（105 项业务、14 项独立诊断）；下文 112、115 项是各阶段日志，不是当前总数。当前业务结论见 [效果验证](../../docs/03-evaluation.md)。

用户以 20 步/10 工具预算复跑超时长案例后，在前两次模型请求中均遇 connection_error，每次约 60 秒，0 次工具、0 个稿件。原始文件归档于 [real-baseline-over-duration-002](../data-validation/real-baseline-over-duration-002/result.json)，[逐字节复核](../data-validation/real-over-duration-retry-verification-001.json) 保存原目录、预算和摘要。业务分支没有运行，不能据此判断扩大预算能否完成修订。

业务模型适配器把 URLError/OSError 统一归为 connection_error；Python 的 [URLError.reason](https://docs.python.org/3.14/library/urllib.error.html) 可能包含另一层异常，因此原业务 Trace 无法区分 DNS、TLS 和被包装的超时。独立诊断脚本读取同一 ModelConfig，复用同一客户端传输与代理/重定向规则，默认查询 [DeepSeek GET /models](https://api-docs.deepseek.com/api/list-models/)；仅指定 --chat 时请求聊天接口，两者均不执行 Agent 业务。

## 执行

在项目根目录使用已配置的本地 .env：

```bash
.venv/bin/python scripts/check_deepseek_connection.py
```

默认请求超时为 15 秒，仅作用于诊断，不修改 Agent 的 60 秒或全局代理。进程环境仍优先于 .env。自动新建 outputs/connection-check-<ID>/report.json，拒绝覆盖旧目录；可用 --timeout 和 --output-dir 自定。打印和文件均不包含密钥、认证头、异常原文、代理地址或响应正文。

| status | 含义与下一步 |
| --- | --- |
| passed | 模型列表接口可达且包含配置模型；仅证明该次列表请求，不保证 Chat Completions 或后续连接稳定。 |
| dns_error | 当前请求路径的域名解析失败。检查本机/WSL DNS；代理模式下也可能是代理主机解析失败，不能直接认定 API 主机故障。 |
| tls_certificate_error / tls_error | 证书或 TLS 连接阶段异常；检查证书、系统时间和代理证书链，保留证书校验。 |
| timeout | 请求或读取响应超时；phase 区分 https_request 与 response_body，仍不保证能定位到 TCP 或 TLS 的具体子阶段。 |
| connection_refused / connection_reset | 连接被拒绝或重置，需核对网络和代理路径。 |
| http_error | 根据 http_status 区分 401 授权、403 拒绝、429 限流或其他服务响应；不打印服务端正文。 |
| model_not_listed | 接口可达但未找到配置模型 ID，需要核对 ID/别名，不直接宣称模型已下线。 |
| invalid_response / configuration_error | 列表格式、配置或依赖需要检查；不能判为生成成功。 |

HTTP 返回码为协议观察，不推断 403 或其他错误的具体平台原因。use_proxy 为 false 时使用当前直连传输；true 时继承系统代理。脚本不会修改 .env、切换代理、关闭 TLS 校验或自动重试。

## 历史阶段：模型列表诊断

- [local-001/report.json](local-001/report.json)：Codex 执行环境，直连、5 秒诊断超时，实际 dns_error，约 0.001 秒。它不是用户宿主环境的诊断结果。
- [112 项测试](unittest-001.txt)：全部通过，无跳过。新增 7 项使用模拟传输，覆盖包装异常分类、HTTP 状态及关闭响应、格式/大小限制、模型列表判断、代理配置复用、凭据过滤与 CLI 文件输出。

生产 Agent 和分类器源码保持原版本，105 项业务测试对应的文件摘要仍可核对；新增的是独立脚本及其测试。旧成功/失败 Trace 保留，不因诊断改写判定。真实超时长有修订及明确未完成退出，但最终修订成功尚未证明。

## 宿主列表成功与聊天接口探测

用户在原终端执行的 [host-models-001/report.json](host-models-001/report.json) 返回 HTTP 200，0.169 秒，包含 deepseek-v4-pro，直连。证明该时刻列表接口可达，不证明聊天请求或持续连通。原报告逐字节归档，[复核](host-models-verification-001.json) 保存原路径和摘要；对应 [旧版诊断脚本快照](diagnostic-models-only.py.txt) 与报告 SHA-256 一致。

检查生产客户端确认 Content-Type 已明确设为 application/json。单独构造缺头请求得到的表单默认值不能用于判断生产请求有问题；生产客户端保持原样。为直接检验聊天路径，扩展独立诊断：

```bash
.venv/bin/python scripts/check_deepseek_connection.py --chat
```

--chat 调用 POST /chat/completions，会产生一次模型请求。它复用生产 DeepSeekModel，声明一个 finish 动作并要求返回 incomplete，只记录动作名，不执行工具或生成视频脚本。探测成功不是 Agent 任务完成或超时长修订证据。默认使用模型配置超时，--timeout 仅覆盖诊断。

status=passed 表示获得预期单动作响应；protocol_error 且 HTTP 200 表示接口返回，但响应未通过本次工具协议要求。HTTP 错误记录状态码，连接异常在适配器合并错误前安全分类；若只有读取阶段的通用错误仍无法细分，会保留 phase/error_code，不猜测原因。密钥、正文、动作参数和异常原文均不输出。

[该阶段 115 项测试](unittest-002.txt) 全部通过；当时新增 3 项验证实际客户端 POST/JSON 头、工具声明与隐私过滤、包装异常/HTTP 类别、HTTP 200 协议异常。112、115 项日志均为诊断脚本历史版本，业务源码未改。[本执行环境 POST 探测](local-chat-001/report.json) 为 dns_error，不能替代宿主结果。

## 宿主 POST 超时与阶段计时

用户 [host-chat-001/report.json](host-chat-001/report.json) 为 POST 超时：60.065 秒，wrapped_by_urlerror=true，尚无 HTTP 状态，phase=https_request。报告及 [当时脚本快照](diagnostic-before-stages.py.txt) 已保留，[摘要](host-chat-verification-001.json) 与原 outputs 字节一致。--cha 被 argparse 的无歧义长选项缩写识别为 --chat，operation 已确认是 POST。

核对实际 Python 3.14.4 的 urllib 源码：do_open 在 h.request 内部的 OSError 外包装 URLError，而等待 HTTP 响应在其后。因此该次错误指向连接建立或发送阶段，不能直接解释为模型生成慢；仍没有证据在 TCP、TLS 和发送之间作进一步结论。前后 GET/POST 是不同时间的新连接，一次 GET 成功不能证明 POST 方法本身是根因。

独立诊断 --chat 现使用标准库 HTTPSHandler/HTTPSConnection 的观测子类，保持默认 TLS 校验、代理及拒绝重定向规则，只记录固定阶段、结果和耗时，生产客户端和 Agent 没有修改：

| phase / stage | 含义 |
| --- | --- |
| connect | 标准库 DNS/TCP 建立；status=dns_error 可明确域名解析错误。代理模式包含连接代理及可选嵌套隧道过程。 |
| proxy_connect | 代理 CONNECT 隧道，仅在相应配置下出现。 |
| tls_handshake | TLS 协商及证书校验。 |
| send_request | 发送 HTTP 头或正文，可能出现多次；不保存发送内容。 |
| wait_http_response | 请求已发送，等待 HTTP 响应；不能仅凭等待时长认定为纯模型推理时间。 |
| response_body | 已取得 HTTP 响应后的读取/解析阶段。 |

嵌套阶段耗时不应简单相加。TLS 校验始终启用，阶段计时不会输出头、正文、异常原文、代理地址或凭据。

如以后需要继续定位，可选择较短诊断超时，保持业务的超时及执行预算；该命令不是当前待执行步骤：

```bash
.venv/bin/python scripts/check_deepseek_connection.py --chat --timeout 15
```

[119 项最新测试](unittest-003.txt) 全部通过；新增 4 项覆盖默认 TLS 验证、连接/TLS/发送/等待阶段区分、日志过滤和代理/重定向配置。测试为模拟连接。[本执行环境阶段探测](local-chat-stages-001/report.json) 为 connect/dns_error，仍不代表宿主原因。
