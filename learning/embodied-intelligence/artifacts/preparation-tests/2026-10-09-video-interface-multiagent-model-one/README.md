# 视频接口单元完整备课：一次同模型多 Agent 测试

2026-10-09，备课版本 v1。用户本次要求只交备课成品供审查，不开展正式教学，不修改真实学习进度，并明确其他相同提示词备课用于对比、不需要读取。本次沿同一模型设置认知规划、材料示范、语义审查三个子 Agent；主 Agent 整合题面、教师参考、支持与首回复。没有读取其他对比备课正文或其他聊天。

**直接审阅：[完整备课.md](完整备课.md)。**它收录下面全部实质内容；代码和核验结果引用各自原件。第一教学回复是文档内的待审草稿，本次没有向学习者正式布置其问题。

| 成品 | 内容 |
|---|---|
| [00-learning-basis.md](00-learning-basis.md) | 最近有效真实记录、原答与帮助的有限支持，以及未完成连接 |
| [01-cognitive-plan.md](01-cognitive-plan.md) | 对象语义、认知主线、整体作品与结束条件 |
| [02-materials-demo.md](02-materials-demo.md) | 完整2×2网格、同一八帧两路接口、保序编码、可信对应恢复与信息边界 |
| [03-encoding-post.md](03-encoding-post.md) | 完整实际策略包的借用与约束、Encoding及目标内Post工作 |
| [04-work-and-reference.md](04-work-and-reference.md) | F→S桥接、连续接口说明、条件不足/新增对应记录的具体题面、教师参考、合法多解和反馈 |
| [05-support.md](05-support.md) | 必要语义、保序/乱序、内容/来源、局部到整体等可直接使用的支持分支 |
| [06-first-teaching-reply.md](06-first-teaching-reply.md) | 第一份教学回复完整草稿，仅供此次审查 |
| [07-audit.md](07-audit.md) | 同模型不同上下文审查的具体发现、修复与剩余限制 |

原相机规格保留为 `(2,4,2,2,3)`，原toy函数仍取左上角红绿值、D=2。材料使用教师构造的夹爪/方块网格，明示其全部输入；没有冒充真实相机数据或学习者代码。示范先把表示与数值、信息可恢复性、来源身份和时间组织分开，再只留一处F→S连接，逐步完成同一接口作品。既有正确部分可以复用；这些工作不是固定数量的通过门槛。

所有可执行学习代码只在 [model_demo.py](../../../code/M0/preparation-tests/2026-10-09-multiagent/model_demo.py)，来源、贡献与运行说明见 [model_demo-README.md](../../../code/M0/preparation-tests/2026-10-09-multiagent/model_demo-README.md)。[materials-check.json](materials-check.json)记录教师标准库核验；PyTorch仅核对官方API，未安装或运行该库，教师结果不归学习者。

依据和约束校验见 [source-manifest.json](source-manifest.json)、[verification.json](verification.json)。现行框架117项指纹核对一致；原学习文件以写前基线和完成后比对保护。本次只新增备课成品与教师代码，没有修改state、原session、goal、plan、assessment、question或既有材料。

本次能审的是内容与准备：实际材料、连贯示范、认知操作、参考和分支是否到位。首回复仍未正式执行；没有新的学习原答、真实学习效果或多Agent相对单Agent增益结论。用户学习时间、设备和能力未新增假设；没有排期、闭卷、保持/远迁移、模型训练或机器人执行。
