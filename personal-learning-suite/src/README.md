# 实际实现入口

2026-10-11方法接入修订：AG2／SK02按用途采用专业变化与约束分析，SK03将实质关系转成必要输入和学习者工作；真实回答的动态适配从C0／Encoding接SK04有限诊断，AG3检查目标关系是否被任务绕过。见 [落实与验证](../../docs/implementation/AI个人学习系统_自由度分析与动态Encoding落实_2026-10-11.md)。

2026-10-07当前修订：收束区分教师解释与学习者整体工作，未完成连接接到已备原作品／实际用途；首次整体支持及关键取舍明确接AG3相关职责，恢复以真实展示事实核旧准备快照。单模型顺序兼任不等于独立Agent启动；等待规则保留。见 [本轮修复及调用核查](../../docs/implementation/AI个人学习系统_单元收束与调用核查修复_2026-10-07.md)。

2026-10-06修订：全部60张Encoding卡与4个Post包完整可读；新单元以认知目标及整体工作备课并实际选法，普通反馈后接已备下一内容，不逐题等待“继续”。资源、接入及实际虚构课堂见 [修复与验证](../../docs/implementation/AI个人学习系统_全策略编译与认知主线修复_2026-10-06.md)。

本目录存放当前 Agent 指导、Skill 源和 Python 辅助实现。日常从 [SK00](skills/personal-learning/SKILL.md)进入；具身智能的真实人工文件学习从 [MODEL_ENTRY](../../learning/embodied-intelligence/MODEL_ENTRY.md)进入。开发规格在 specs，设计研究在 docs；文件指导可按需读取，尚未安装自包含包，Python 真实模型与个人记录承载仍未绑定。

当前课程／单元启动先备好本次主要内容、知识联系、实际材料和主要问题，再开始展示；完整要求在 [内容准备](skills/learning-teaching/references/design-whole.md)，修改依据、虚构备课及验证见 [本次修复记录](../../docs/implementation/AI个人学习系统_本次学习完整备课修复_2026-10-05.md)。一次性解释和已有合格安排恢复保留简洁路径。

当前全套来源比较及新上下文实际首回合见 [原意复审](../../docs/audits/AI个人学习系统_全套Skill与Agent原意复审_2026-10-05.md)，第六阶段当时的指令修复与检查见 [历史记录](../../docs/implementation/AI个人学习系统_教学内容重构_第六阶段实施与验证_2026-10-05.md)。维护／明确试用时按 [有限验证](skills/personal-learning/references/verification.md)分别核内容、执行、真实学习与投入，日常课无需加载；验证报告及测试夹具留在 validation，原研究／设计留在 docs。

## 四个 Agent

新增的 [coordinator/replay.py](coordinator/replay.py) 是执行层只读历史回放组件，不是Agent，也不是src/runtime的真实学习记录入口。[第一批交付](../../docs/implementation/AI个人学习系统_任务与产物协调器_第一批只读回放_2026-10-13.md)包含案例与验收结果。

[coordinator/workspace.py](coordinator/workspace.py)提供第二批文件任务、快照、候选及采用检查；本地操作员负责绑定角色，现有学习入口与旧运行器边界未改。[第二批交付](../../docs/implementation/AI个人学习系统_任务与产物协调器_第二批最小提交闭环_2026-10-13.md)说明接口、测试与部署范围。

[coordinator/reliability.py](coordinator/reliability.py)是第三批本地可靠性扩展，提供明确期限的结果等待、同事务增量事件、操作回执和只读恢复检查。[第三批交付](../../docs/implementation/AI个人学习系统_任务与产物协调器_第三批并发与恢复_2026-10-13.md)包含真实多进程/硬退出验证；普通CLI不自动升级第二批历史工作区。

| Agent | 文件 | 责任 |
|---|---|---|
| AG0 | [AG0-coach.md](agents/AG0-coach.md) | 入口、教学执行、真实发生事实、恢复与控制 |
| AG1 | [AG1-design-planning.md](agents/AG1-design-planning.md) | 目标、关键教学设计、投入与连续性安排 |
| AG2 | [AG2-materials.md](agents/AG2-materials.md) | 来源、内容、材料用途与纠错 |
| AG3 | [AG3-assessment.md](agents/AG3-assessment.md) | 表现证据、条件化判断、评估与复核 |

这些是角色定义，不能据文件存在推断四个独立模型已启动。

## 七个 Skill

| Skill | 实际入口 |
|---|---|
| SK00 学习总入口 | [personal-learning](skills/personal-learning/SKILL.md) |
| SK01 目标 | [learning-goals](skills/learning-goals/SKILL.md) |
| SK02 内容与材料 | [learning-materials](skills/learning-materials/SKILL.md) |
| SK03 教学 | [learning-teaching](skills/learning-teaching/SKILL.md) |
| SK04 评估 | [learning-assessment](skills/learning-assessment/SKILL.md) |
| SK05 计划与连续性 | [learning-planning](skills/learning-planning/SKILL.md) |
| SK06 策略 | [learning-strategies](skills/learning-strategies/SKILL.md) |

每个 Skill 的 `references` 是其正常依赖，和 SKILL.md 保存在一起。共享语义见[契约](../contracts/shared-contracts.md)，资源见[资源说明](../resources/README.md)。

## 运行程序

任务与产物协调采用[src/coordinator完整实现](coordinator/complete.py)，日常通过[Agent简化接口](coordinator/agent_api.py)和[简短指南](../specs/coordinator-agent-guide.md)取得必要状态、固定正文并提交明确意图；[技术入口](../scripts/coordinate_preparation.py)及[完整协调说明](../specs/coordinator-protocol.md)按需查询。真实模式只登记原工作区文件的协调元数据，专业决定保留给原角色。

开发 CLI 为 [personal_learning.py](runtime/personal_learning.py)；B5 顺序集成为 [entry_b5.py](runtime/entry_b5.py)，B6 受控串行宿主为 [network_b6.py](runtime/network_b6.py)，共享保存为 [learning_store.py](runtime/learning_store.py)。各专业服务在 runtime，仅用于其声明的虚构开发输入；日常人工教学按 SK00 指导与所在课程的文件协议开展。

具体调用、开发边界及历史验收见[套件 README](../README.md)，项目各类文档见[总导航](../../README.md)。
