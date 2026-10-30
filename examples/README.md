# 输入、实际输出和验证材料

当前核心循环可运行。当前 [新提示词验证](prompt-validation/README.md) 包含 87 项通过测试、五条 Mock 案例及一次真实连接失败。旧提示词的成功路径、Trace 和指纹见 [历史 Agent 运行索引](agent-validation/README.md)，不能代替新提示词真实验证。

## 输入与资料

- [normal/input.json](normal/input.json)：新手、轻松、通用短视频、30 秒以内。
- [insufficient-information/input.json](insufficient-information/input.json)：缺少主题。
- [no-materials/materials.json](no-materials/materials.json)：空资料集。
- [no-materials/input.json](no-materials/input.json)：空资料场景的完整需求。
- [unrelated-materials](unrelated-materials/materials.json)：仅“支持调节音量”的无关合成事实，需求仍为字幕。
- [over-duration/input.json](over-duration/input.json)：5 秒上限，不保证真实模型首稿超时；需要核对实际 Trace。
- [产品事实](../data/materials.json) 和 [品牌规则](../data/brand_rules.json)：用户指定的最小合成资料。

## 证据范围

旧提示词真实正常路径已记录改写检索、受限表达被拒后的修订、v2 重检和完成。真实检索故障注入路径记录一次明确模拟的工具错误，以及真实模型的查询调整和后续修订。缺信息案例在 real 模式下由基础校验直接返回问题，没有调用模型。

Mock 路径另覆盖正常、超时长、事实违规、故障恢复、无素材、缺信息、执行上限和提前完成申请。Mock 只验证流程，不证明真实模型具备相应效果。真实模型的超时长修订与稳定性仍待验证。

[历史工具记录](tool-validation/README.md) 的输入是人工脚本，不是模型生成；历史 15/37 项测试日志的源码指纹也不等于当前版本。不得将这些材料混同为完整真实模型验收。

.env、note/ 和日常 outputs/ 不提交。公开证据不包含 API 密钥、认证头或模型内部思维过程；保留简短行动依据、版本对应的实际观察和必要失败记录。
