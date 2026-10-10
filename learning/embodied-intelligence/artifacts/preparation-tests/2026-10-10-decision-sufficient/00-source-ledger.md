# 来源、阅读范围与证据身份

日期：2026-10-10。对应 [DA-2 学科实质分析](00-disciplinary-analysis.md)。仅为备课来源账本，不是学习者阅读记录或真实掌握证明。检索使用原论文、作者机构/会议公开全文；搜索摘要仅用于定位。网页发布时间/抓取时间不代替论文年份。正文为原创分析与自拟例子，未长段引用原文。

## 用户指定方法文件

| 来源 | 实际取得范围 | 本次作用/限制 |
|---|---|---|
| [研究报告.md](<E:/文献资料/学习系统架构设计/docs/research/2026-10-10-disciplinary-analysis/研究报告.md>) | 文件全文读取；初次工具输出截去的中部已用分段读取补齐 | 采用问题—理由—判断—边界、任务与整体互查、专业/教学/个体未知分开、认知反向回修。它是本地综合研究建议，不声称这些组合已被实验证明普遍有效。 |
| [单元学科分析工作底稿.md](<E:/文献资料/学习系统架构设计/docs/research/2026-10-10-disciplinary-analysis/单元学科分析工作底稿.md>) | 全文 | 采用实质命题、专家实践重建、任务理由、替代比较、简化界限与下游交接；不机械要求填满所有栏。 |

## 一手专业来源

| ID | 原始来源 | 实际阅读范围 | 支持的关键内容 | 本次没有声称已取得什么 |
|---|---|---|---|---|
| S1 | Grimm, Barreto, Singh, Silver (2020). [The Value Equivalence Principle for Model-Based Reinforcement Learning](https://proceedings.neurips.cc/paper/2020/file/3bb585ea00014b0e3ebe4c6dd165a358-Paper.pdf), NeurIPS 33 | PDF正文 §1–4，Definition 1、Properties 1–4、Propositions 1–3、损失定义；其余实验/附录未作为关键依据 | VE针对政策集与函数集的Bellman更新；扩集合增加约束；一般预测损失与VE目标不同 | 没有逐行复核全部证明、复现实验、证明有限latent网络达VE |
| S2 | Grimm, Barreto, Farquhar, Silver, Singh (2021). [Proper Value Equivalence](https://papers.nips.cc/paper/2021/file/400e5e6a7ce0c754f281525fae75a873-Paper.pdf), NeurIPS 34 | PDF正文 §2–3，Definition 1、Propositions 1、3–5、Corollary 1；MuZero讨论只用于边界提醒 | PVE是指定政策的完整价值保持；所有确定性政策下的规划充分性结果；原设定γ<1/MDP | 没有把PVE当任意有限rollout/神经latent的定理，没有逐行复核附录 |
| S3 | Li, Walsh, Littman (2006). [Towards a Unified Theory of State Abstraction for MDPs](https://thomasjwalsh.net/pub/aima06Towards.pdf), ISAIM | PDF §2、§3.3–3.6，Definitions of abstraction、Theorems 2–5 与弱抽象反例说明 | model-irrelevance保持reward和到抽象类转移概率；仅最优动作保持不足以保证聚合MDP规划 | 没有声称所有抽象层级在任意POMDP/任意搜索器中同样有效 |
| S4 | Gelada, Kumar, Buckman, Nachum, Bellemare (2019). [DeepMDP: Learning Continuous Latent Space Models for Representation Learning](https://proceedings.mlr.press/v97/gelada19a/gelada19a.pdf), ICML / PMLR 97 | PDF §2.1–4.2；Lipschitz设定、latent reward/Wasserstein transition损失、Theorems 1–3及local/global解释；bisimulation连接开头 | 奖励与编码转移分布的控制关联；全局与政策访问分布局部误差不同；理论条件必需 | 未用任意欧氏consistency替代其分布条件；未复现实验或全文逐行证明 |
| S5 | Schrittwieser et al. (2020; arXiv v2 Feb 2020). [Mastering Atari, Go, Chess and Shogi by Planning with a Learned Model](https://arxiv.org/pdf/1911.08265)；正式 [Nature 页面](https://www.nature.com/articles/s41586-020-03051-4) | 作者arXiv PDF §2–3、Figure 1及loss式1；结果与限制相关段落（内部状态无环境语义、确定性dynamics、imperfect-information不直接处理）；Nature页面直接打开失败但书目摘要可定位 | representation/dynamics/prediction；reward/value/policy目标；MCTS；真实方法不要求像素重构 | 未把性能结果当PVE精确满足；未验证代码或宣称一般POMDP最优 |
| S6 | Hansen, Su, Wang (2024, ICLR; arXiv submitted 2023). [TD-MPC2: Scalable, Robust World Models for Continuous Control](https://arxiv.org/html/2310.16828v2) | 作者arXiv HTML §2–3，式1–6、Figure 3组件；OpenReview PDF遇验证页，故未以其正文为已读 | decoder-free joint-embedding/reward/TD目标；Q尾值、policy prior、latent有限序列优化 | 没有逐项复核104任务结果或实现；不把局部MPC视为一般最优反馈计划 |
| S7 | Kaelbling, Littman, Cassandra (1998). [Planning and Acting in Partially Observable Stochastic Domains](https://people.csail.mit.edu/lpk/papers/aij98-pomdp.pdf), Artificial Intelligence 101:99–134 | 作者MIT机构PDF §3 belief/state estimation和belief MDP、§6.7 plan structures；Cassandra站点副本打开失败，换用机构原件 | belief作为历史充分统计；MAP状态不一般充分；反馈/分支计划与固定动作序列不同 | 未声称任意RNN latent就是belief，未证明本地玩具环境以外的近似信息状态界 |

备课中关于 RSSM/Dreamer 的一行仅作为此前单元接口和方法对照，不用来引入新的性能或最优性主张；具体真实架构若展开，应在材料生成阶段取得官方原文对应部分。发现的[DreamerV3 Nature 原文](https://www.nature.com/articles/s41586-025-08744-2)网页直接打开失败，检索结果含components，但本次未标全文已读；不得从该检索片段制造详细算法/实验结论。

## 自拟内容与推导

- 配送路由、100像素、reward-only编码、H1尾值、p阈值、inspect、背景奖金和风险/coverage扩展均为 AI 自拟。所有数值由明示reward/transition规则计算，非论文实验、非教学实证、非学习者记录。
- 数值复算：好/坏 shortcut为9/−5.4；坏路模型A regret9.4；好路reward-only regret5；belief阈值47/72；p=.8/.2收益6.12/−2.52；inspect反馈/固定safe/固定shortcut为5.35/3.1/1.12；背景奖金坏路b_bg=1收益12.6；诊断pixel MSE .01/.99。
- \(2\epsilon+\eta\)候选决策损失界在正文给出完整初等推导。它相对于固定起点/目标/候选集合的**统一候选评分误差**，没有由像素loss或经验TD loss估出ε，也不用于宣称一般无限时域性能。
- 教学排序、任务设计和预期错误均是备课假设。没有对当前学习者作能力诊断，也没有验证教学效果。
- DA-2 补充的有限时域 Bellman 闭合证明是正文按奖励、抽象类分布、共同合法动作、兼容终止及类上尾值条件写出的可复核归纳，不冒充原论文全部无限时域证明。零尾值和一般可表示尾值分别给出，政策提升接口明示。有限时域可允许γ=1。
- DA-2 的随机支持例为AI自拟：P的两点为±1，Q的两点为±2，各半，均值都0；U(z)=z²时价值期望为1和4，γ=.9备份为.9和3.6。它针对均值不足的逻辑可能性，不是DeepMDP实验或真实模型的实测失败。
- DA-2 来源没有扩展检索；修订依据是认知分析的具体回问与框架/数学审查对背景状态、合法动作、尾值和终止接口的前提补足。没有新增教学效果证据。

## 引用/专业核验边界

1. 固定奖励、折扣、时域、合法动作与政策信息结构，之后才谈“充分”。同一个词在不同论文里保留不同数学对象。
2. 原始论文定理、方法说明、论文实验结果、本地数学演示、教学假设分别标示。自拟环境只揭示逻辑可能性，不证明某架构在真实数据中更优。
3. 原始来源已读到定义/条件/机制相关部分；未读完整证明或未复现实验的项目明示。不得以“官方论文”消除其设定限制。
4. 来源链接直接指向原文或正式页面，没有保留不可追溯的工具turn标记。

