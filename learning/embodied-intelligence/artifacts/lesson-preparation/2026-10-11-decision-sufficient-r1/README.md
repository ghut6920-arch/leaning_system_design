# 面向决策的潜在世界模型：备课审查入口

日期：2026-10-11；版本 r1；状态：prepared_for_review。当前完成备课，尚未正式教学、取得学习者原答或形成能力判断。真实学习进度和共享框架保持原状。

专业终点：给定任务、在线信息、规划需求、模型能力和评价证据，判断世界模型需要保留什么、哪些误差影响决策，以及怎样选用、修正和检验模型。整体作品是一份技术决策建议；案例附记最后汇入同一份报告。

## 先看实际成品

| 成品 | 可直接审查的内容 |
|---|---|
| [认知主线与设计](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/artifacts/lesson-preparation/2026-10-11-decision-sufficient-r1/03-cognitive-design.md>) | 候选 C1–C5、M0–M6 主线、教师与学习者分工、完整策略的版本／实际借用、Encoding与Post交替、连续父产物与停止条件 |
| [实际讲义与连贯示范](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/questions/visible/decision-sufficient-preparation-r1/materials.md>) | 对象与评价式→原任务可压缩→观测误差低却决策错→奖励改变后的接口冲突；受限价值等价、独立期望工具、真实方法接口与历史示范 |
| [具体问题](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/questions/visible/decision-sufficient-preparation-r1/tasks.md>) | T1有支持重建，T2新随机评价，T3新动作，T4规划配置，T5新部署技术建议；条件、数据与允许资料均已给出 |
| [教师参考](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/questions/teacher-reference/decision-sufficient-preparation-r1/reference.md>) | 完整计算、合法多解、可接受／应拒用结论、两条综合实验及结果分支、短反馈和返回；拟教学时不随题自动展示 |
| [必要支持分支](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/questions/backup/decision-sufficient-preparation-r1/support.md>) | 对象时点、信息冲突、概率工具、目标量、新动作、规划账本、报告组织；每支都有实际正文、够用条件、证据限制与返回位置 |

拟教学顺序：M0–M3→T1→M4→T2→M5→T3／T4→M6→T5。正常反馈后接已备内容，在需要学习者贡献处等待；可分段停，不把每次答题当作新单元。本次只供审查，不按这个顺序启动课堂。

## 学科依据与审查

| 原件 | 用途 |
|---|---|
| [学科实质分析](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/artifacts/lesson-preparation/2026-10-11-decision-sufficient-r1/01-disciplinary-analysis.md>) | 从关键选择、专业关系、条件变化到教学价值；实际求解代表任务，区分表达、训练、规划和证据 |
| [来源与读取范围](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/artifacts/lesson-preparation/2026-10-11-decision-sufficient-r1/02-source-register.md>) | 指定两份研究原件、Value Equivalence／MuZero／TD-MPC／TD-MPC2 的实际阅读和限制 |
| [反向任务检验](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/artifacts/lesson-preparation/2026-10-11-decision-sufficient-r1/07-reverse-review.md>) | 先提出改变条件后的核心关系问题，再查实际成品；分别核目标深度、教学输入、题面代选与证据边界 |
| [教师侧数值核验](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/experiments/decision-sufficient/preparation-r1/numerical-verification.md>) | 本次实际程序运行、手算对照、最终代码指纹与未覆盖范围 |
| [范围与过程依据](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/artifacts/lesson-preparation/2026-10-11-decision-sufficient-r1/00-scope-and-provenance.md>) | 用户范围、角色实际承担、中断与恢复、框架和真实控制基线 |
| [交付核验](<E:/文献资料/学习系统架构设计/learning/embodied-intelligence/artifacts/lesson-preparation/2026-10-11-decision-sufficient-r1/08-delivery-verification.md>) | 成品定位、链接／文本检查、控制及框架未变的最终确认 |

## 这次顺序变化实际带来了什么

学科Agent先完成内容包，认知Agent随后据专业判断设计，发现 T2 缺少可直接使用的有限期望工具，回交学科Agent补公式、对象与另一线性例；再落实到 M4。这个修补增加了可用前提，同时保留新平方任务中的判断工作。

认知Agent保存设计后因用量限制中断，root接任讲义、题面和支持；学科Agent完成教师参考。审查Agent先独立拟反向问题，中断后恢复读取实际成品，发现行内公式显示问题；修复后又实际回读。真实分工和完成范围有据，不称盲评或真人专家核验。

A落实在01的选择与条件研究；B落实在03与实际题面中教师提供／学习者承担的区分；C落实在07先定反向问题后查作品。没有把 A/B/C 写回共享 AG2／SK03／AG3 规则。

## 当前边界

主线覆盖有限规划、期望收益、表示信息、动作覆盖、末端评价和新部署的诊断设计。风险约束在学科稿中有合法备用例，本次未展开为教学主线；不能由 T2 推出任意风险规划能力。完整搜索算法、训练实现和一般最小充分表示证明亦未列为当前要求。

备课内容与用途已核，数值代码已实际运行；教学执行、真实学习效果和多Agent净收益没有由本次获得验证。预算、设备与个体先验仍未知。所有文件是 AI 备课材料，代码原件在 code/；没有保存虚构学习者答案、创建学习事件或修改进度。

审查可以查看教师参考。以后若进入测试学习，需按实际已读讲义、参考和核验输出解释表现；“尚未正式教学”不会抹掉审查中已发生的接触，也不能据文件状态声称全新无提示测试。
