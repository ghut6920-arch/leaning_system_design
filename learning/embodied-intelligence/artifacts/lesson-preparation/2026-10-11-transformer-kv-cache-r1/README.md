# Transformer Attention：KV Cache 与长上下文推理备课

2026-10-11 / revision 1。交付用途：学习系统测试备课、供审查。未开展正式教学，未形成学习者能力结论。

主线是：**Attention运算 → 逐层因果不变量 → 有效前缀与Prefill／Decode时序 → 容量、计算与读取 → 按约束选择方案 → 长上下文质量与条件更新**。拟采用的一份连续作品为“推理审计与方案说明”，保持同一产物接续，不按一道小题或一次“继续”重新开课。

审查可直接阅读 [完整备课.md](完整备课.md)。它由下面原件汇编，包含实际材料、示范、问题、教师参考、支持和审查；不是另一个学习进度文件。成品中“请完成”的内容是预备题面，本轮不需作答。

| 原件 | 可直接审查的内容 |
|---|---|
| [00 范围与接入](00-scope-and-framework.md) | 当前请求原文、控制、框架取得、实际委派、保存边界 |
| [01 学科研究](01-disciplinary-analysis.md)、[02 来源台账](02-source-register.md) | 专业对象、机制、条件、合法替代、实际阅读定位与未核范围 |
| [03 认知设计](03-cognitive-design.md) | 目标建议、知识联系、师生分工、完整策略借用、Encoding与Post主线 |
| [04 实际材料](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/questions/preparation-tests/transformer-kv-cache-20261011/visible/04-materials.md) | Q/K/V完整手算、逐层归纳、实际两层轨迹、chunk mask、成本和容量、三张图、可核日志样本 |
| [05 连续工作](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/questions/preparation-tests/transformer-kv-cache-20261011/visible/05-continuous-work.md) | A推理审计→B GQA预算与方案→C前缀／位置／窗口条件修订 |
| [06 教师参考](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/questions/preparation-tests/transformer-kv-cache-20261011/teacher-reference/06-reference.md) | 完整理由、数值锚点、合法多解、信息不足、反馈、整体评价边界 |
| [08 必要支持](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/questions/preparation-tests/transformer-kv-cache-20261011/backup/08-support.md) | 具体输入、调用信号、够用条件、同一作品返回与缩时路径 |
| [07 反向审查](07-reverse-review.md) | 先于成品形成的专业基准、实质缺口、修复与范围内结论 |
| [09 交付核验](09-delivery-verification.md) | 教师运行、图像视查、保存与真实进度完整性、未验证效果 |

[代码与贡献说明](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/code/transformer-kv-cache/preparation-r1/README.md)、[教师数值说明](teacher-run/numerical-walkthrough.md)、[实际结果JSON](teacher-run/checks.json)可以回查。源代码为无训练的标准库两层toy，数值结果不代替真实模型／GPU／学习者实验。

完整成品保存后供用户审查；本轮没有教学采用、排期或后续真实学习承诺。
