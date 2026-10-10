# M7.2「Flow Matching 桥接」备课审查入口

2026-10-10，revision 1。当前为备课成品审查，不开展正式教学，不写入真实学习进度、表现或成绩。用户相关先验、学习预算与运行环境未知；原大纲 10 小时没有采用为个人承诺。

本次按照指定顺序完成学科分析后交认知设计，再生成材料与问题。认知设计未发现必须回改的学科缺桥，因此没有模拟反向修订。实际讲解、题面、教师参考、备用支持、代码、运行结果和两张图均已生成并按各自用途核查；本入口是供用户审查的完整成品。

## 建议审查顺序

| 成品 | 审查重点 |
|---|---|
| [00 实质学科分析](00-disciplinary-analysis.md) · [来源审计](00-source-audit.md) | 问题、对象、理由、真实竞争方案、代表任务解与简化边界，是否保留原用途 |
| [01 认知主线](01-cognitive-design.md) · [02 策略适配](02-method-config.md) | 关键工作如何接成一份连续作品，完整策略实际借用什么 |
| [03 实际讲解与连贯示范](../../../questions/preparation-tests/M7-2-flow-matching-20261010/visible/03-learner-material.md) | 是否能从数据追到标签、参数、局部场、采样、误差和动作接口，是否存在专家才能补出的跳跃 |
| [04 完整整体题面](../../../questions/preparation-tests/M7-2-flow-matching-20261010/visible/04-main-work.md) | 新记录计算、风险理由、采样组织、实验解释和条件取舍是否仍由学习者承担 |
| [05 教师参考](../../../questions/preparation-tests/M7-2-flow-matching-20261010/teacher-reference/05-teacher-reference.md) | 完整解、合法多解、判断依据与帮助限制是否可用 |
| [06 备用支持](../../../questions/preparation-tests/M7-2-flow-matching-20261010/backup/06-support-branches.md) | 是否有可直接使用的支持正文，以及具体够用条件和返回原作品的位置 |
| [07 教师代码与运行核验](07-code-and-run-review.md) · [08 内容审查](08-content-review.md) | 实际实现、运行、图和解释是否符合规格，核查范围如何受限 |

所有题面／输入、备用支持和教师参考使用 questions/ 原件；所有学习与绘图代码在 code/。本目录只组织分析、方法、核验和教师输出，不复制成第二份学习进度。

## 整体认知主线

\[
\text{数据/噪声/条件}\to (x_t,u)\to
\text{平方回归与共享参数}\to E[U\mid x,t,c]\to
\text{ODE/Euler}\to\text{条件分布与误差/成本判断}.
\]

Encoding 采用 S05 连贯范例、R02 的受条件约束桥接与 D02 单因素对照。Post 采用关系整合与给定候选中的条件选用，接回同一整体作品；未强加闭卷恢复、延迟复测或四包固定流程。实际资源全文、版本和借用操作见方法记录。

教师示范提供必要对象、规则和可追踪的理由；学习者工作保留新记录计算、信息来源说明、风险理由重建、采样核心实现或规格、误差参照选择、实际结果解释和具身轴映射。完整教师代码已被查看后，后续实现按支持下修改／追踪解释，不能倒记为自主实现。

主例是每类 Gaussian 的 2D 条件 FM，有解析场和精确解，可分开查学习场与积分。辅助同 c 双峰是解析结构对照；当前仿射回归器没有类内多峰训练证据。OT 成本反例只否定独立配对已最优，没有把本单元扩大为完整 OT 课。

## 交付边界与恢复

当前全部材料均为 prepared for review。链接供审查，不表示正式教学已经呈现、学习者已作答或目标已通过。学科正确性、材料功能、教师运行、真实学习效果和多 Agent 净收益分别成立；后三者中真实学习与协作收益没有观察。

如果后续要求开始教学，沿本单元及同一作品恢复：先核当前控制和实际接触，已有合格产物优先审查，必要输入先给，普通反馈后接已备下一连接。这里没有建立正式排期或自动提醒，也没有改变旧 M0 断点。

本次实际阶段与版本核查记录见 [备课过程](99-workflow-log.md)。[进度完整性核对](09-progress-integrity.json)确认既有 state、goals、plan、assessment、sessions、course、modules 的 75 份文件数量与字节哈希均未变，框架 118 项指纹仍相符。

## 实际核验结果

- 八组数学与接口检查通过：训练更新、hat 特征、有限差分梯度、解析解、Euler 误差、状态／时间／更新次数、异常接口、双峰与 OT 成本反例。
- NumPy 已实际用 100000 条 CFM 训练记录拟合共享参数；25000 条 held-out 的 CFM coordinate-MSE=.784192475，field coordinate-MSE=.000557859。oracle 没有用作训练标签。
- 8192 个固定新噪声样本按 c 比较 N=1/4/16/64/128；2048 与 4096 步 learned 参照的二维范数 RMS 差约 .000260441，仍保留有限参照资格。
- [轨迹图](figures/01-trajectories.png)与[采样比较图](figures/02-sampling-comparison.png)由生成 Agent 和根入口实际查看。数据标签、坐标、时间和参照对象对应正确，无裁切；SVG 原件同目录。
- 内容审查发现的代码链接、输入／监督分路与量纲说明已经修正；风险常数首次使用处的 Q(t) 定义亦补齐。初审快照与后续处理保留在内容审查及过程记录中。

复现代码与来源贡献见 [代码项目说明](../../../code/M7/flow-matching-prep-20261010/README.md)，教师实际原输出见 [summary-r1.json](teacher-run/summary-r1.json)和[按类指标 CSV](teacher-run/metrics-r1.csv)。这些结果只支持本例的教师内容与实现核验；个体学习收益、真实机器人效果和额外 Agent 的净收益未验证。

交付检查见 [10-delivery-checks.json](10-delivery-checks.json)，文件版本／SHA-256清单见 [delivery-manifest.json](delivery-manifest.json)。本包最后实质核验的14份Markdown中59个本地链接无缺失，教师源代码与运行记录的SHA一致；清单只用于定位版本，不证明学科正确或学习效果。
