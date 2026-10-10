# Encoding 高级策略：从知识结构到可迁移的内部模型

配套文件：[60张操作卡](02_Encoding微操作与提问库.md) · 导师提示词（原阅读版 Encoding研究与策略库.html 未随本项目提供） · [机器可读策略库](04_Encoding策略库.json)

研究日期：2026-09-24。版本：2.0（依据升级规范完成科学性审查与文档同步）。面向个人学习系统与 AI tutor。根据用户提供的《深度研究.md》确定问题范围；文档中的假设和示例作为待检验问题处理。

## 1. 最重要的判断

**高质量 encoding 的设计单位，应当是“需要修正的知识表征”，而不是“要使用的学习技巧”。**

例如，同样是“讲不清一个机制”，可能分别源于不知道组件、缺少一条因果边、把相关当因果、不知道适用条件，或无法把局部变化传播到整体。它们需要不同的学习任务。反复要求“深入思考、用自己的话解释”，无法可靠地区分这些问题。

建议建立如下闭环：

**知识结构 → 当前表征缺口 → 最少必要认知操作 → 可观察的学习产物 → 对照证据修正 → 无帮助的新情境检查。**

这里的“最少必要”“表征缺口诊断”和下面的选择算法是本报告的**设计综合**，不是已经被整套实验验证的统一理论。研究支持若干构件；整套系统仍需实测。

六类动作适合作为策略库入口，但不是六个互斥的脑过程，也不是必须依次完成的六个阶段。同一个任务可以同时涉及比较、关系映射与重表征。把案例比较归到 Differentiate，是按其主要教学目的索引。

Encoding 也并非与 retrieval 完全隔离：激活先验知识和预测会调用已有记忆；撤去材料后的解释兼具提取成分。本报告聚焦初次建模及紧接其后的修正，延迟测试用于检验学习，不把它冒充 encoding 本身。

**v2.0 的具体目标：**在目标任务需要的范围内，形成能够说明关系类型、适用条件、不变量及允许变换的知识表征。更高级意味着判断更准确、限制更清楚、需要时能变换和检验；不意味着画更大的图、问更多层“为什么”或完成更多种策略。

升级保留六类动作与60张卡。新增提问、局部诊断流程和组合仍是H级设计；逻辑正确性、策略家族的实验支持、本系统的实际学习收益，必须分别判断。停止标准仍以目标够用为准，允许保留不影响当前判断的黑箱。

## 2. 证据怎么读

这是**定向文献检索与跨传统证据综合**，不是注册过的系统综述。以原始论文、期刊全文、作者或研究机构版本为依据，重点覆盖 2016—2026，同时保留解释关键机制的经典研究。没有进行穷尽数据库检索、正式偏倚风险评估或重新计算效应量。

全文使用三个层次，不能混为一谈：

| 标签 | 含义 | 可以据此做什么 |
|---|---|---|
| **E1：聚合证据** | 元分析、系统综述；仍可能异质、存在发表偏倚 | 选择有较广支持的策略家族，不能保证每个模板有效 |
| **E2：情境实证** | 某类实验、课堂或技能任务中的结果 | 在相近人群、材料、目标下优先尝试 |
| **H：设计推论/理论** | 从已有证据推导的微操作、调度规则或新框架 | 作为可检验假设，不能宣称确定提升学习 |

每条策略还需标明证据环境：**实验室记忆、类别/因果学习实验、课堂知识学习、复杂 STEM、程序/技能、真实教育部署**。同一研究可以跨两个标签。“有元分析”不等于对所有领域强证据；“真实课堂”也不等于已验证长期迁移。

策略库中的具体中文提问、例子、停止规则均为原创教学设计。它们借鉴所列文献，**没有逐条经过随机试验**。尤其不能把整类 self-explanation 的平均效果，分配为每个“为什么”问题的效果。

**读新增内容时再作一次分层：**“平行四边形有一个直角即可判矩形”是数学条件结论；“用这个对照训练条件敏感性”是教学设计；“此训练优于另一方案并改善迁移”则需要比较研究。前两项成立不自动证明第三项。卡片里的H标记针对设计与收益外推，不表示所有学科内容本身都只是猜测。

证据范围应落在具体主张上：比较研究支持比较家族，不直接验证本系统的条件组合表；支架研究不直接验证每次局部展开后的最优返回时机；多表征研究不直接验证新增的信息审计问法。对仅有摘要或邻近任务证据的来源，保留原台账限制。

## 3. 哪些前沿进展值得改变系统设计

| 证据 | 可采纳结论 | 不应推出的结论 |
|---|---|---|
| Fiorella 2023 生成学习框架 [F01](https://link.springer.com/article/10.1007/s10648-023-09769-7) | 解释、可视化与动作表征有不同功能；是否产生有效加工受知识、策略和动机条件影响 | 画图、教学、总结可以互换；只要产出了东西就学会了 |
| Thomann 与 Deutscher 2025 数字提示元分析，68 项实验 [F02](https://www.researchgate.net/publication/391489104_Scaffolding_through_prompts_in_digital_learning_A_systematic_review_and_meta-analysis_of_effectiveness_on_learning_achievement) | 提示的效果取决于设计；总体 d=.394，发表偏倚校正后估计 d=.220 | 每次加提示都有效；这些数据已经证明现代 LLM 的某种实时调度最优 |
| 2026 数字提示设计框架 [F03](https://link.springer.com/article/10.1007/s10648-026-10164-1) | 把提示的内容、触发时机与适应方式当成可设计变量 | 新框架的每个规则都有独立因果验证 |
| Makransky 等 2025 ChatTutor 两项课堂实验 [F04](https://link.springer.com/article/10.1007/s10648-025-10039-x) | 结构化生成任务与反馈值得使用；高中研究即时优于普通 ChatGPT 和重学，延迟优于 ChatGPT、未显著优于重学 | 所有比较均显著，或长期效果已经确定。大学研究部分结果不显著，且论文摘要和结果叙述不完全一致，宜按结果段保守解释 |
| Bastani 等 2025 高中数学现场实验 [F05](https://doi.org/10.1073/pnas.2422633122) | 有 AI 时的成绩与独立能力可能分离；GPT Base 撤去后成绩比对照低约 17%（相对变化） | AI 必然损害学习；提示式 GPT Tutor 已被证明提升独立考试。该组与对照未见显著差异 |
| Kestin 等 2025，194 名大学物理学生的交叉随机研究 [F06](https://www.nature.com/articles/s41598-025-97652-6) | 精心设计的 AI tutor 在特定课程即时测验中可以有效 | 普通聊天界面等效；结果证明长期保持、远迁移或所有学科优势 |
| Cho 2026 AI-GLM 理论分析 [F07](https://link.springer.com/article/10.1007/s10648-026-10210-y) | 记录“关键关系是谁生成的”，区分 AI 支持、替代与提供待分析材料 | AI-GLM 是已验证的最优教学算法；论文明确属于概念分析 |

据此，一个值得采用的前沿设计方向是：**AI 负责提供可靠材料、选择任务、给适量支架与反馈；学习者负责关键判断、关系补全、边界辨认和模型修正。**这是一项有构件证据支持的设计综合，而非单篇论文已经证实的完整方案。

AI 生成一张正确的图，不等于学习者建立了正确模型；学习者批判一张 AI 图，也不自动代表高质量加工。必须检查其能否独立指出错误、解释修正，并处理一个新情况。

### 六类动作中最影响决策的证据

| 结论 | 设计含义 | 证据 |
|---|---|---|
| 预问主要改善目标内容；2025元分析中目标题g=.66、未预问题g=.01 | 不能只问一个事实，就假定整章结构都被激活 | [OS03](https://link.springer.com/article/10.1007/s10648-025-10075-7) |
| 数学示例学习有聚合支持；与先探索后讲授的研究使用不同对照 | 新手程序优先示例；有相关知识的概念探索可有界进行；不把两类效应量相互排名 | [OS06](https://journals.sagepub.com/doi/full/10.3102/00346543211019105)、[OS07](https://www.danamillercotto.com/uploads/4/7/7/2/47725475/barbieri_et_al__2023__we_meta-analysis.pdf) |
| 比较的收益取决于比较目标、对应关系与支持 | 区分类内找共性、类间辨界、同题异解选方法 | [DI01](https://scispace.com/pdf/learning-through-case-comparisons-a-meta-analytic-review-21w9vk760p.pdf)、[DI02](https://cdn.vanderbilt.edu/t2-my/my-prd/wp-content/uploads/sites/3147/2021/01/Rittle-JohnsonStarDurkin2020_Current-Directions_CompareandExplain_Revision2.pdf) |
| 交错对不同内容与测量目标不一致 | 区分类别辨别和新例生成；不统一强制交错 | [DI05](https://www.uni-wuerzburg.de/fileadmin/06020400/2019/Brunmair_Richter_in_press__2019_META-ANALYSIS_OF_INTERLEAVED_LEARNING.pdf)、[DI06](https://journals.sagepub.com/doi/full/10.1177/14757257241248155) |
| 自解释有聚合支持；额外绘图支架不自动有效 | 让学习者补理由、对照并修正关键关系，避免只改写或美化图 | [RR01](https://link.springer.com/article/10.1007/s10648-018-9434-x)、[RR03](https://link.springer.com/article/10.1007/s10648-025-10067-7) |
| 教学预期显著调节“通过讲授学习”的收益 | 若选讲授，在学习前说明讲给谁、解决什么困难；未预告的教回仍可诊断，但不承诺同等学习增益 | [RR04](https://link.springer.com/article/10.1007/s10648-024-09871-4) |
| 具体先行未在复杂物理中表现出普遍优势 | 选择最容易表达目标关系的表示，再明确连接具体与抽象 | [DI11](https://link.springer.com/article/10.1007/s10648-020-09581-7)、[DI12](https://researchportal.helsinki.fi/en/publications/concreteness-fading-in-learning-secondary-school-physics-concepts/) |

这些效应量是各自对照下的标准化差异，不是个人收益百分比。证据台账保留研究环境、访问范围和推断边界。

**本次升级如何由证据改变设计：**变化学习综述提醒区分变化维度与学习条件，因此I03、I04、I09记录变化了什么，而不把“更多样”当统一剂量。[DI09](https://eprints.gla.ac.uk/272070/2/272070.pdf) 支架与认知负荷研究提示依据当前知识提供帮助，因此S01、S08、S10按组件诊断、撤除及回测；不能由此承诺局部展开完全不增加负担。[OS08](https://link.springer.com/article/10.1007/s10648-023-09817-2)

多表征的DeFT框架分别考虑设计、功能与学习者任务，指出表征可以提供互补信息，也会增加对应与理解的要求；因此X06检查信息来源和转换任务，而非预设所有表示完全等价。[U01](https://www.researchgate.net/profile/Shaaron-Ainsworth/publication/222410911_DeFT_A_conceptual_framework_for_learning_with_multiple_representations_Learning_and_Instruction_16_183-198/links/5ea69ecb45851553fab2dd69/DeFT-A-conceptual-framework-for-learning-with-multiple-representations-Learning-and-Instruction-16-183-198.pdf) 迁移分类框架提示不同变化维度应分别描述，因此I04、I09采用多维记录，不构造统一距离分数。[U02](https://pdf.retrievalpractice.org/transfer/Barnett_Ceci_2002.pdf) 两者是经典框架，用于补足约束，不能因本次新增便称为2026年的新实证。以上四项是设计依据，新增组合的效果仍待验证。

## 4. Encoding Operation Taxonomy：六类动作向下拆解

下表是导航；完整操作卡及好坏问题见配套《微操作与提问库》。每类均拆到可执行任务，避免只把 Relate 做深。

| 宏动作 | 目标表征变化 | 核心微操作 | 可观察产物 |
|---|---|---|---|
| Orient 定向 | 从漫无目标接收，变成有问题与待修正预期 | 目标问题、事实预问、方向预测、机制候选、粗模型、结构预览、矛盾定位、先验激活、置信标记 | 一个预测、候选模型或明确的未知项 |
| Scaffold 支架 | 从同时处理过多孤立元素，变成可加工的局部结构 | 前置诊断、预训练、结构分块、完整示例、子目标标注、部分补全、渐隐、分段揭示、表征对齐、按表现调整帮助 | 能解释并完成一个关键步骤 |
| Relate 关系化 | 从术语集合，变成带类型、方向与条件的关系 | 层级/整体部分、依赖、因果链、必要充分、共同原因、动态传播、反馈、干预、反事实、条件重要性 | 有依据的关系边与可检验预测 |
| Differentiate 辨析 | 从“看起来相似”，变成抓住判别结构 | 对齐比较、最小差异、正反例、近错例、边界、例外、特征隔离、诊断特征、错误解释对照、适用条件对照 | 能说出决定结论的区别并处理近邻案例 |
| Instantiate 具体化 | 从抽象标签，变成有语义锚点且能脱离单一例子 | 典型例、控制变化、多样例、极端例、边界例、类比映射、类比失效、具体与抽象往返、多表征对应、动作/操作 | 例子与规则的对应关系，以及不对应之处 |
| Re-represent 重表征 | 从复制材料，变成组织、转换与压缩 | 定向自解释、机制解释、受约束生成、示意图、概念/因果图、图式互译、案例到规则、带条件压缩、教回、模型修订 | 保留关键关系的新表征与修改理由 |

**选择何种图，要由关系决定。**层级结构用树或集合；机制用有明确语义的因果图；流程用条件分支；动态过程用状态随时间变化的曲线或表；数量关系用公式与图像。给所有内容画同一种思维导图，容易把不同关系都变成无类型连线。

这里的“内部表征变化”是设计目标，无法直接从笔记外观读出。外部图、解释和答案只是观测证据，必须结合迁移表现判断。[F08](https://education.asu.edu/sites/g/files/litvpz656/files/lcl/chiwylie2014icap_2.pdf)

每次任务明确五件事：当前表征哪里不够；要做哪种变换；哪些关系与条件必须保持；允许改变或补入什么；用什么任务检查。这里的不变量随目标而定：改写文字可能保持全部目标命题，改变实例可能只保持抽象关系，补入实测数据则会增加信息，三者不应混称等价转换。

| 六类动作的深化重点 | 产生什么可检查内容 | 何时足够 |
|---|---|---|
| Orient | 目标→已知基础→具体未知→候选→分歧预测→证据→修订 | 有可检验缺口；候选无法区分时能说明缺什么 |
| Scaffold | 整体目标→必要组件→局部帮助→接口→返回整体 | 局部修复支持原目标，无须展开所有内部细节 |
| Relate | 有类型与条件的关系；正向预测与逆向诊断分开 | 目标推断有依据，不能识别的部分明确保留 |
| Differentiate | 对齐、条件性判据、合法近例/非例 | 能按条件处理近邻例与信息不足例 |
| Instantiate | 规则逐项落地；表面变化与结构变化分开 | 有诊断性的实例覆盖，不追求穷举变化组合 |
| Re-represent | 信息保留/丢失/新增及推断权限 | 表示能支持目标任务，关键约束没有被改写掉 |

另将四类对象分开记录：**学科参考模型、学习前置依赖、对学习者的暂定诊断、当前呈现的支架**。“学A有助于学B”不是“A在物理上导致B”；材料中显示了一条关系也不表示学习者掌握了它。四类记录可互相引用，但不混成一张无类型网络。

## 5. 用“结构属性”选择操作，而非给知识贴唯一标签

一个知识点可以同时具有多个属性。例如负反馈控制兼有数学关系、因果机制、动态系统和程序决策。建议对以下属性做低/中/高或有/无标记，不把它们强行相加成一个总难度：

| 结构属性 | 最需检查的缺口 | 优先操作 | 检验任务 |
|---|---|---|---|
| 类别边界密集 | 不能区分近邻概念 | 最小差异→诊断特征→边界例 | 给新近错例，解释纳入/排除理由 |
| 存在方向性机制 | 只会重复“A 导致 B” | 因果链补全→中介解释→单变量干预 | 切断中介，预测首先改变什么 |
| 动态、延迟、反馈 | 把短期效应当最终效应 | 局部过程→分时段模拟→反馈检查 | 分开预测即时、过渡、稳态 |
| 层级/整体部分 | 混淆组织层级与因果方向 | 关系类型标记→跨层连接 | 解释整体变化如何由局部相互作用产生 |
| 程序与选择点 | 会照做，但不会选择何时做 | worked example→条件行动配对→异常诊断 | 改条件后选择下一步并给理由 |
| 数量/函数关系 | 会代入，但不会解释变量关系 | 图式互译→控制变量→极限/量纲检查 | 改一个量，保持另一个不变，说明曲线如何变 |
| 抽象不变量 | 被例子表面吸引 | 对齐多例→找保持不变的关系→新实例 | 表面变化很大时仍找到同一结构 |
| 规则依赖条件 | 过度推广 | 正常例→近失效例→条件压缩 | 给一个必须拒用该规则的情况 |
| 任意约定/事实 | 没有可推导的深层结构 | 精确辨认、适量组织、必要语义联系 | 准确区分与提取；不硬编机制 |

“因果”只能用于有因果含义的内容。词法约定、数学定义、历史命名不需要发明一个机制。数学证明需要明确前提与合法推导，不能用生动类比替代；合法反例可以否定全称命题，但并非每项证明都需要反例。

| 特殊内容 | 需保留的性质 | 不应强加的解释 |
|---|---|---|
| 数学定义与证明 | 对象域、量词、前提与每步合法推导 | 用若干正例或生动类比代替普遍证明；要求每项证明都含反例 |
| 概率关系 | 事件、条件、基准率与不确定性 | 把高概率当必然；由P(B\|A)直接反推P(A\|B) |
| 程序 | 输入约束、前/后置条件、不变量、分支与终止条件 | 仅记固定步骤序列；不同区间约定混用 |
| 约定与命名 | 精确对应、使用语境及容易混淆项 | 为任意约定编造必然机制 |

例如已知规则描述统计趋势，一次例外不一定推翻它；若命题断言“域内所有对象都满足”，一个合法反例就足以否定。任务判据随命题类型改变。

## 6. Strategy Selection Matrix：实际如何只选两三个操作

下列组合是**H：基于构件证据的启发式配方**。“两三个”是控制每轮任务负担的产品默认值，不是工作记忆容量定律。长课程可以分多轮。

| 知识属性 × 学习者状态 | 目标/主要风险 | 本轮选择与顺序 | 暂缓项 | 进入下一轮的条件 |
|---|---|---|---|---|
| 新概念；新手；近邻很多 | 准确分类；边界混淆 | 典型例示范→正反例对照→诊断特征说明 | 自由生成大量反例 | 新近错例分类正确且理由正确 |
| 因果机制；前置知识不足；交互高 | 基本机制理解；空想因果 | 前置示例→局部因果链补全→定向解释 | 整系统反事实与主因排名 | 关键中介、方向与条件正确 |
| 因果机制；已有局部 schema | 干预迁移；相关误当因果 | 粗模型→证据对照修订→单变量干预 | 无约束模型扩张 | 新干预预测与机制一致 |
| 动态系统；中等基础；负荷中 | 系统推理；忽略延迟 | 局部传播→反馈回路→时间/边界比较 | 一次讨论所有非线性现象 | 能区分即时与长期效果 |
| 新程序；新手；错误代价高 | 正确操作；步骤误用 | 完整示范→关键步骤补全→分支条件解释 | 先自由试错 | 能独立选择下一步且无关键错误 |
| 程序；熟练；例外频繁 | 灵活应用；惯性套用 | 异常例诊断→替代程序比较→新情境执行 | 冗长逐步示范 | 改变触发条件后能切换程序 |
| 抽象规则；已有基础 | 迁移；过早抽象 | 对齐两例→关系抽象→表面不同的新例 | 十个互不对齐的故事 | 新例能映射角色并说出适用条件 |
| 数学关系；会算但理解浅 | 概念理解；表征分离 | 公式↔图像→控制变量预测→边界检查 | 单纯改写公式 | 双向转换不丢掉定义域/假设 |
| 任意事实；低复杂度 | 精确认识；相似项混淆 | 事实预问→正确答案定位→相似项辨认 | 强行机制化 | 对应关系准确；后续另配提取练习 |
| 同一错误且高置信 | 概念修正；错误固化 | 明确错误命题→替代解释→新案例验证 | 让其重复讲错模型 | 能解释原错误为何失败 |
| 专家；高先验；目标创新迁移 | 条件变化下的判断 | 边界扰动→结构比较→模型压缩/修正 | 冗余支架 | 能指出新问题与旧 schema 的不同 |

先验知识要按当前内容诊断。“数学好”“学过一遍”不足以判断会不会某个子技能。用一个前置步骤、一个判别案例和一个短解释比自报“初级/高级”更有信息；具体题数按任务调整。

负荷不能仅凭回答慢来判定。联合观察：是否反复丢条件、在多个表示间迷失、无法完成前置步骤、生成无关细节，以及主观吃力程度。答错但机制接近可能是有价值的困难；连变量是什么都不清楚时应补支架。

**选择还要说明为何值得增加这一步。**只需查所属类别时，短定义和一个近错例可能足够；需要预测随时间的响应时，再加状态变量与时间表示；只需使用黑箱输出时，先检查接口，不自动追问内部机制。每个追加操作应能修正一处具体错误，或提供原任务没有提供的诊断信息。

本轮不是必须凑足“两三个”：一个操作已满足目标就结束。组合有功能重叠时合并，如S07与X02都用于同一个缺失步骤，不应重复填空再计作两个独立收益。选择的合理性要由无帮助表现及成本回测，而非由类别覆盖率判断。

## 7. 关于“操作深度”：采用多维进展，不采用八级排行榜

本次检索没有找到与文档八级顺序完全对应、被普遍接受且逐级验证的 encoding taxonomy。ICAP 描述参与/知识建构模式；生成学习研究讨论选择、组织、整合；因果推理区分观察、干预、反事实；这些不是同一维度。[F01](https://link.springer.com/article/10.1007/s10648-023-09769-7)、[F08](https://education.asu.edu/sites/g/files/litvpz656/files/lcl/chiwylie2014icap_2.pdf)

可把文档中的八层改成**五条可分别诊断的轴**，作为 H 级设计综合：

| 轴 | 从弱到强的表现 | 常见误判 |
|---|---|---|
| 关系精确性 | “有关”→关系类型、方向、条件明确 | 连线很多就是结构丰富 |
| 解释完整性 | 标签→中间过程→可检验机制 | 字数多就是机制解释 |
| 边界敏感性 | 单例适用→近错例→条件变化 | 总能套用就是迁移好 |
| 扰动推演能力 | 重述→预测变化→干预/反事实并说明假设 | 编出反事实故事就是理解因果 |
| 跨表征与跨情境保持 | 复制→转换保持关键关系→新情境重建 | 换词换图就是形成新表征 |

不同任务选择不同轴。学术语无需追到系统涌现；学反馈机制则不能停在名词识别。只有在模型、参数或证据允许时，才问变化的数值幅度；否则应允许答案为“方向可判断、大小不可确定”。

**十二项细化检查与五条轴的关系（H）。**以下是把升级要求操作化后的检查表，不是另立十二级，也不是声称文献已经验证这十二项为量表。条目互有交叠，按目标选用；不适用项留空，不能加总为“深度总分”。

| 细化检查项 | 主要对应轴 | 可以观察的表现 |
|---|---|---|
| 1. 关系类型、方向与对象 | 关系精确性 | 不把部件、定义与因果混写 |
| 2. 成立条件与条件组合 | 关系精确性、边界敏感性 | 同一线索在不同背景下作不同判断 |
| 3. 中间机制及证据 | 解释完整性 | 补出必要中介，未知处不编造 |
| 4. 层间接口及粒度 | 解释完整性 | 展开后仍能接回整体预测 |
| 5. 定义域与失效边界 | 边界敏感性 | 区分域外、近似误差和信息不足 |
| 6. 近邻辨析与合法反例 | 边界敏感性 | 改例后仍满足非目标约束 |
| 7. 时间与状态 | 扰动推演能力 | 即时、过渡、稳态分别判断 |
| 8. 干预与反事实 | 扰动推演能力 | 写出变更项、保持项及模型假设 |
| 9. 逆向诊断与可辨识性 | 关系精确性、扰动推演能力 | 多解释相容时不强选唯一原因 |
| 10. 表征信息与推断权限 | 跨表征与跨情境保持 | 区分重表达、新证据和新假设 |
| 11. 实例变化与迁移条件 | 跨表征与跨情境保持、边界敏感性 | 分别检验错用原则和漏用原则 |
| 12. 压缩、重建与修订 | 跨表征与跨情境保持、解释完整性 | 用精简表示恢复目标所需推理 |

另外单列**掌握证据条件**与**执行成本**：材料是否可见、提示多少、是否新题、间隔多久；用了多少时间、何种帮助、是否可持续。它们不是知识关系本身，却决定凭什么判断学会、是否值得采用。即使图和解释复杂，也不能跳过这两份记录。

## 8. Relate 中最容易被伪深度掩盖的七个问题

**1. 结构边与因果边分开。**“A 属于 B”“A 是 B 的部分”“A 与 B 共同变化”“改变 A 会改变 B”不是同一种关系。先标边类型，再推演，避免把分类图当机制图。

**2. 机制解释补中间过程。**要求“实体/过程 → 相互作用 → 状态改变 → 结果”，同时允许标未知。增加一个听起来专业的中介名词，并不完成解释。

**3. 必要、充分、促成和背景条件分别问。**“没有 A 是否不可能发生 B？”与“有 A 是否一定发生 B？”检验不同命题；概率性现象还需说明机会、基线与条件，不能强行二值化。

**4. 观察、干预、反事实分开。**观察到 A 高不等于外部把 A 调高；“若当时 A 不发生”需要指定保留哪些背景事实以及采用什么模型。学习者生成的反事实是模型检验工具，本身不是证明真实世界因果关系的证据。

**5. 动态模拟加时间索引。**先让学习者说 t0→t1→t2 的局部变化，再讨论回路。正反馈不必然失控，负反馈不必然稳定；回路增益、延迟和非线性都可能改变结果。实际判断需要领域模型。

**6. 主因必须先定义“重要”。**效应幅度、必要性、上游位置、可操纵性、瓶颈与当前条件下敏感度是不同标准。最上游变量未必有最大可实现干预收益。先限定比较范围与指标，再问排序；没有模型或数据时，不要求虚构贡献百分比。

**7. 系统级表示逐层联结。**component→interaction→mechanism→behavior 是有用的组织模板，但不是一切知识的通用架构。每次扩展只增加与学习目标有关的关系，并保留一个局部可验证例子。完整网络图可以作为外部支架，不必让新手一次从空白生成。

上述精细问法主要是跨因果推理、解释与系统学习的设计综合。具体学习收益的证据不均衡；反事实、动态模拟和条件权重尤其不能仅凭逻辑复杂，就自动排在示例学习或对齐比较之上。其情境证据包括反事实教学实验 [RR05](https://languageandlearninglab.com/wp-content/uploads/1-s2.0-S0022096522000959-main.pdf)、因果装置学习 [RR08](https://cicl.stanford.edu/papers/gong2023active.pdf) 与反馈推理难点测量 [RR12](https://pmc.ncbi.nlm.nih.gov/articles/PMC9582828/)；三者不能互相替代。

**逆向诊断要允许多解。**正向问“模型与输入已知，会出现什么结果”，逆向问“观察到结果，可能是哪种模型或参数”。同一观测可对应多个解释。先列候选对观察的预测，再寻找能区分的证据；当前数据不足时明确报告不可辨识。第12节给出同稳态、不同速度的可计算例。主动因果学习的实验是邻近依据，不能把其结果当作这套教学流程已获直接验证。[RR08](https://cicl.stanford.edu/papers/gong2023active.pdf)

**把黑箱作为带接口的模块。**最小接口记录为：输入、输出、适用条件、目标需要保留的性质、内部未知。只在接口不足以支持目标预测或作答暴露相关错误时展开。补齐后必须回测整体；跨层比较和切换仍有认知成本，不能称为无负担增加深度。

**反事实的合法性有两层。**现实干预需检查能否实施与保持背景；思想实验可采用明确理想化的结构，但必须模型内自洽，并标明现实适用限制。“可推演”不等于“已证明现实因果”。因果边、条件概率和定义恒等关系也不能仅因都写成箭头而互换。

## 9. 顺序：哪些可优先采用，哪些需要测试

| 序列 | 证据地位 | 可执行条件与边界 |
|---|---|---|
| 完整示例→补全→独立完成 | 有示例/渐隐研究支撑 [OS07](https://www.danamillercotto.com/uploads/4/7/7/2/47725475/barbieri_et_al__2023__we_meta-analysis.pdf)、[OS10](https://www.cs.cmu.edu/~bmclaren/pubs/NajarMitrovicMcLaren-LearningWithITSAndWorkedExamples-UMUAI2016.pdf)、[OS12](https://onlinelibrary.wiley.com/doi/full/10.1111/cogs.12086) | 新手复杂程序的合理起点；渐隐跟随表现，不按固定分钟数 |
| 先尝试解决→明确讲授与整合 | productive failure 有聚合证据 [OS06](https://journals.sagepub.com/doi/full/10.3102/00346543211019105)、[DI04](https://aaalab.stanford.edu/assets/papers/2011/Practicing_versus_inventing.pdf) | 必须是有设计的任务和后续讲授；不能改写成任意主题先自由猜测 |
| 对齐案例→解释共同结构→新案例 | 案例比较/类比研究支持构件 [DI01](https://scispace.com/pdf/learning-through-case-comparisons-a-meta-analytic-review-21w9vk760p.pdf)、[DI03](https://groups.psych.northwestern.edu/gentner/papers/GentnerLoewensteinThompson03.pdf) | 完整三步未在所有领域验证；比较前是否给规则取决于目标与先验 |
| 具体例→抽象表示→回到新例 | 有概念与情境证据，领域差异大 [DI10](https://scholarworks.iu.edu/dspace/bitstreams/2c814639-f4c7-4091-a6eb-5e6e834bc546/download)、[DI11](https://link.springer.com/article/10.1007/s10648-020-09581-7)、[DI12](https://researchportal.helsinki.fi/en/publications/concreteness-fading-in-learning-secondary-school-physics-concepts/) | 每次说明两种表示的对应；不能保证总优于抽象先行 |
| 明确错误命题→否定与替代解释→新例 | refutation 研究支持纠错结构 [DI08](https://experts.nau.edu/en/publications/the-effectiveness-of-refutation-text-in-confronting-scientific-mi/) | 不把错误句单独反复呈现；反馈后检验新情境 |
| 粗模型→材料→模型修订 | 有预测、生成与模型学习的邻近证据 | 本组合属 H；没有找到其普遍胜过“讲授→总结”的直接证据 |
| 对照→解释 vs 解释→对照 | 无普遍优胜顺序 | 前者可暴露差异，后者可给新手比较维度；按局部困难试验 |
| 因果链→干预→反馈→边界 | 合理综合，非已验证统一序列 | 拆成多个微循环；不会局部机制就不强行升级 |

选择序列时区分“准备学习”和“已经掌握”。先探索可能提高接下来从讲授中获益的能力，即使探索阶段答得不好；示例先行可能更快形成可靠基础。要比较等时条件下的后续学习和迁移，而不是只比较探索阶段得分。

**认知依赖应由具体任务决定。**比较至少需要能辨认双方相关元素；解释需要必要术语和关系规则；从实例抽象需要足够的条件信息；生成合法新例需要能核验规则。欠缺其中一项时先补该项，而不默认执行“实例→比较→解释→抽象”的固定全序列。

局部修复采用有返回路径的流程：保存父目标→根据作答提出暂定缺口→用小任务区分备选解释→必要时提供局部帮助→检验子目标→返回新的父目标任务。预算到达或找不到有价值的展开时停止并记录未知。一次错答不足以精确还原内部模型，持续失败应重审诊断。

## 10. 什么时候先生成，什么时候先支架

| 情况 | 建议 | 原因及反馈方式 |
|---|---|---|
| 有相关知识；任务短；错误可定位；稍后有可靠答案 | 先做一个有约束的预测/尝试 | 让后续材料对应明确差距；展示正确依据后修改原答案 |
| 有部分知识；机制有若干缺口 | 先给部分图/选项/示例，再补全 | 保留关键关系给学习者做，减少搜索空间 |
| 关键术语、表示规则或前置步骤尚缺 | 先示范与解释 | 自由生成难以建立有效候选模型；补齐基础后再生成 |
| 高置信错误模型反复出现 | 提供针对性反驳与替代机制 | 不能仅说“再想想”；记录旧断言与新依据 |
| 正确性无法由材料或工具校验 | 不把生成答案写入已掌握模型 | 标记待核实；转为比较假设或询问证据 |
| 错误后果高的实际操作 | 在可靠指导/安全模拟中学习 | 不以无指导试错作为现场操作教学 |

“反馈”不是只给正确选项。至少说明：哪里错、依据是什么、正确关系是什么，并让学习者完成一次新的判别或预测。是否需要立即反馈或短延迟反馈取决于任务；本系统默认不让未经核验的错误模型继续支撑多个新推论，这是风险控制设计，不是宣称即时反馈永远最优。错误生成与纠正的研究综合见 [OS11](https://www.annualreviews.org/content/journals/10.1146/annurev-psych-010416-044022)。

还应防止四类常见失真：有趣细节抢占注意；类比把不成立的关系带入目标领域；多个相似例子导致过早概括；AI 对流利但错误的解释给予肯定。解决办法分别是目标相关性筛选、类比失效标记、诊断性变化与反例、依据明确的反馈。

**生成多少并非关键，留下哪项加工才关键。**AI可以提供候选模型、图中节点、范例前半段或可靠数据，但要指出仍由学习者完成的是关系选择、条件判断、预测还是纠错理由。若完整解释和对应关系都已给出，再让学习者复述，只能记录相应支持条件下的表现。

受约束生成允许合法答案空间仍有多个结果；开放生成也可有清楚评价标准。两者不是“有创造力/没创造力”的等级。前置不足时提供最小必要基础，已有基础时保留有意义的认知工作；之后用较少支持的新题检查独立性。

## 11. Encoding Decision Algorithm

这是可实现的启发式控制流程，尚不是经过学习收益优化的模型。不要给每个步骤伪造精确权重或适应阈值。

```text
输入：学习材料、可信参考、学习目标、学习者先验表现、时间预算

1. 提取目标表征
   标出：核心元素、关系类型、适用条件、常见误区、允许推断的范围。
   区分材料明确给出、可合理推导、尚未知；不自行补成“权威模型”。

2. 诊断当前缺口
   用一个短任务检查目标所需的前置技能或关键区别。
   区分：知识缺失、关系错接、边界误用、表示不熟、程序选择错、负荷过高。
   无证据时记录“未知”，而不是默认为不会或已经会。

3. 先过生成条件检查
   若前置不足或高交互 → 提供示例/预训练/部分表示。
   若存在稳定错误模型 → 明确对照、解释与修订。
   若已有相关 schema 且能纠错 → 可先短预测或有限生成。

4. 选择本轮必要操作（2—3个仅为默认上限附近的启发式，一个已足够就不追加）
   优先能暴露或修正当前关键缺口的操作。
   优先与材料、人群、目标相近的研究支持。
   删除功能重复、无新增诊断信息或负担明显过大的操作。

5. 编译成学习者任务
   指定对象、限制条件、要求的关系、产物格式与判据。
   一次提出一个主要认知要求；不同时抛出一串“为什么”。

6. 观察并反馈
   对照参考模型检查正确性、机制、条件和表示一致性。
   无法验证 → 标未知/补来源，不奖励流利表达。
   关键错误 → 示例或提示；部分正确 → 局部补全；稳定正确 → 渐隐。

7. 检查修订是否发生
   让学习者指出“改了哪一处、为什么”，再做一个新近邻案例。
   只有重述 AI 解释 → 换表面形式检查；未过关则回到对应缺口。

8. 停止本轮
   目标相关关键关系正确，能处理新例，且没有关键条件错误 → 收束。
   时间耗尽或负荷上升 → 缩小范围，记录未解决项；不继续堆策略。
   日后用无 AI 的延迟任务检查保持和迁移，更新对策略效果的判断。
```

系统应保存的最小记录：`内容片段、目标、先验依据、缺口、操作ID、任务、学习者初答、提示程度、纠错依据、修订、新例表现、待核实项`。聊天轮数和文字长度不能替代这些数据。

**v2.0 编译与记录补充（H）：**

- 生成任务前写清允许变更项、不变量、禁止无依据新增的信息及可接受的“未知”答案。
- 局部展开时记录父目标、子目标、诊断依据、接口、返回条件、用时边界；子任务完成后回到父目标新题。
- 外部记录分开保存学科参考、前置依赖、学习者诊断与当前支架。记录规范可独立实施；本次策略JSON保持原字段结构，不据此宣称运行中的导师已经实现自动诊断。
- 每项表现附材料可见性、提示程度与独立性；学习产物、掌握证据条件、执行成本分开判断。

“停止本轮”只表示当前范围有足够证据或预算结束，不表示长期掌握已经确立；未解决项保留，不用连续升级问题来掩盖。

## 12. 一套有答案判据的完整演示：学习一阶负反馈系统

以下为原创演示，用一个明确模型约束推理，避免凭语言猜“系统效应”。假定学习者会基本比例关系与变化率，但不了解反馈。

**教学模型**：状态 x 的变化率满足 `dx/dt = u − kx`，输入 `u = a(r − x)`；a、k 为正常数，r 为固定目标。假设没有延迟、执行器不饱和。x 与 r 的单位相同，u 的单位为状态量/时间，a 与 k 的单位为时间的倒数。这是简化模型，不代表所有真实控制系统。

**目标**：能解释局部纠偏机制、预测固定目标变化后的响应，并知道负反馈不必使误差归零。

| 环节 | AI 的任务 | 预期认知操作 | 答案判据 |
|---|---|---|---|
| 诊断 | “若输入保持不变，x 增加，流失项 kx 如何变？” | 检查比例前置知识 | k 固定时增加；不清楚则先示例 |
| 第 1 轮：局部补全 | 提供 `r−x → u → dx/dt → x`，问“x 暂时偏高，哪条关系首先响应？逐步标方向。” | 因果链与方向关系 | 误差下降、输入下降，产生纠偏作用；须保留同时存在的流失项 |
| 反馈 | 对照两式修正箭头，并问“哪一个变化由公式直接给出？” | 依据定位与模型修订 | 区分代数依赖与状态随时间变化 |
| 第 2 轮：表示转换 | “代入 u，写成关于 x 的一个式子；由变化率为零求稳态。” | 公式重表征 | `dx/dt=ar−(a+k)x`；`x*=ar/(a+k)` |
| 第 3 轮：扰动与边界 | “在原稳态把 r 提高：x 能瞬间跳到新稳态吗？若 a 加大，误差一定为零吗？” | 时间推演与条件辨析 | 连续状态不瞬间跳变；稳态向新值移动；有限 a、k>0 时一般仍有误差 |
| 无帮助新例 | “增加 k 而保持 a、r 不变，新稳态怎样？你依据哪一关系？” | 新情境检查 | 对 r>0，新稳态下降；依据稳态式而非背诵反馈口号 |

这个过程跨三轮使用操作，而非一次要求新手完成整系统解释。若学习者不会微分方程，前两步只用方向与离散变化表，先补变化率概念再引入公式。

进一步想研究“延迟是否导致振荡”，必须先给带延迟模型或可靠模拟结果；不能从当前无延迟模型任意编出结论。这里的“反事实”“极限情况”都受模型假设约束。

**用同一个模型区分不同误解。**下列推导均限于上述一阶、线性、固定r、a/k为正常数且无延迟和饱和的教学模型；不是对真实系统的额外实验结论。

| 学习者判断 | 具体缺口 | 针对性任务与判据 |
|---|---|---|
| “负反馈最终总能让x=r” | 忽略流失项与稳态条件 | 求x*=ar/(a+k)；对r>0且有限a、k>0，误差rk/(a+k)>0 |
| “r一变，x立即跳到新值” | 混淆瞬时输入与连续状态 | u可发生跳变，x需按微分方程连续演化；不能把状态图画成同样的阶跃 |
| “只知道x*就知道a和k” | 把逆向多解当唯一解 | 列两组给出同稳态的参数，再找可区分的动态观测 |
| “负反馈都按这条曲线变化” | 越过模型边界 | 指出延迟、饱和或其他状态变量出现时需重新建模，不能从此例直接外推 |

**逆向诊断算例。**设r=10且已确认达到稳态，观察x*=5，则只能推出a=k。a=k=1与a=k=2都相容（时间单位一致）。由初始状态x(0)=0出发，两条解分别为`x(t)=5(1−exp(−2t))`和`x(t)=5(1−exp(−4t))`，其时间常数分别为0.5和0.25个时间单位。因此在已知输入、初值与观察时间的前提下，过渡响应可以区分它们；相同稳态本身不能。

若能在此模型下可靠估计稳态比例g=x*/r及衰减率λ=a+k，则可反推a=gλ、k=(1−g)λ。这里要求r非零、模型与测量条件成立，并有足够动态数据；仅有某时刻x=5且不知是否稳态时，连a=k也不能推出。测量噪声还会影响参数估计，不能把教学中的精确值当实测精度。

以上算例连接O05的分歧预测、R05的逆向诊断、R06的时间索引与X06的信息核查；按学习者具体错误选用，不要求每次完成整套。

## 13. 另外三个短例：看起来类似的学习困难，为什么选不同策略

**概念分类：随机分配与随机抽样。**给两个最小差异案例：一个从人群随机抽样后统一接受处理；一个从方便样本招募后随机分配处理。让学习者标“随机发生在哪一步”，再说明分别关联何种推断问题。最后给一个两者皆有的案例。目标是诊断特征，不需要完整因果系统图。

**程序学习：二分查找。**先展示数组、边界和循环条件，再只留一个分支的边界更新让学习者补全；随后提供含两个元素的边界案例，要求指出为何一定缩小区间。目标是条件—行动与不变量；仅背步骤或看动画不够。具体实现需明确区间是否包含端点。

**抽象原则：加权平均。**并排给两组人数不同的班级平均分，问“为什么直接平均两个均分会出错”；映射人数到权重，再转到价格/数量的新情境。最后给权重相等例，让学习者说明何时简单平均成立。重点是多例对齐和条件压缩，不是搜集很多生活故事。

**条件性判据的补例。**在非退化简单平面四边形范围，“有一个直角”不足以判断矩形；若背景已知是平行四边形，同一特征就足够，因为其余角受平行关系约束。它说明判据依赖背景与联合条件，不能据此断言所有分类都可用单一诊断特征。这里是逻辑关系，不是已估计出的统计交互效应。可接D02、D03、D04。

**表面×结构矩阵的补例（H）。**以“是否正比例”为目标，先写清“同一场景”为表面相似的临时标准，x为合法数量且常数固定：

| | 目标结构保持：正比例 | 目标结构不保持 |
|---|---|---|
| 相同收费场景 | y=2x，无固定费用 | y=2x+10，含固定费用 |
| 不同领域场景 | m=ρV，同种均匀材料且ρ固定 | C=C₀+ρV，容器总质量含非零皮重C₀ |

四格分别帮助暴露正确迁移、受表面诱导的错用和忽视结构的漏用。保持其他难度大致可比；新领域知识不足时先补背景，否则失败未必是迁移问题。最终撤去“正比例”标题，在混合题中自主选择规则。表面、角色、数量、表征、条件、领域先验和提示变化分开记录，不穷举全部组合，不汇成统一距离。

**近反例要合法。**正方形变为非正方形菱形时可保持四边等长，角必须按几何约束联动；不能只在图上随意改一个角同时宣称其他角都不变。若用角度差衡量距离，可以构造任意接近的反例，未必存在唯一最近反例。变换后要重新核查全部条件。

## 14. 真正值得投入的高级策略

这些不是已确立的学术术语，而是本报告建议优先试验的产品设计。

**按错误选择下一问。**学习者漏了中介就补中介，混淆类别就出最小差异，忽视时间就给短期/长期对照。优于预先写死十轮提问的假设，需要用同时间预算进行测试。

**保留模型修订记录。**让学习者只标“删哪条边、加哪个条件、改哪个方向及其依据”。这样能区分增加术语与改变结构；是否提升保持仍需验证。

**用能区分候选模型的问题诊断。**如果两个解释对常规案例预测相同，就找它们预测不同的合法干预或边界例。先验证任务答案，再交给学习者。该设计借鉴因果学习，不应把 AI 猜测的差异当事实。

**跨表征检查保持了什么。**图像转公式后，要求指出变量、方向、条件和限制是否保持；再反向转换。把评分重点放在关系一致性，减少“漂亮但无意义的图”。

**记录认知劳动的归属。**区分 AI 给出的解释、学习者补的关系、反馈后修正以及无帮助完成的部分。不要用 AI 帮忙生成的长答案直接推断学习者掌握程度。[F07](https://link.springer.com/article/10.1007/s10648-026-10210-y)

**把新证据用于更新配方。**每个操作卡同时保留“策略家族证据”和“本系统效果”。低先验、高先验分开分析，防止平均有效掩盖某群体受损。

这些设计直接归入原有类别，避免在60张卡之外再平行堆叠一套概念。优先落实到四组可检验任务：

| 原有卡片 | 改进内容 | 本轮可检查结果 |
|---|---|---|
| D02—D06 | 条件组合、诊断性及合法近反例 | 能说清同一特征何时足够、何时不足 |
| X04—X07、I06 | 信息审计、推断权限与冲突检查 | 不凭箭头补函数，不把新假设冒充转换所得 |
| I03—I04、I09 | 多维变化与表面×结构矩阵 | 减少错用与漏用，并记录所需领域先验 |
| S09—S10、R03、R10 | 带接口与返回条件的局部展开 | 子问题修复后，原问题确实改善 |

它们具有明确设计理由，也能写出失败判据；目前不能声称“四项必然提升成绩”或给出优势排序。内容逻辑检验通过，只是进入学习效果试验的前提。

## 15. 如何验证系统，而不是只验证输出好看

推荐先测试两个最容易混淆的设计问题：

1. 同样的内容与时间，固定序列和按错误选择任务相比，能否提高无帮助的新题表现？
2. 同样的任务，AI 直接解释和“学习者补关键关系→反馈”相比，能否改善延迟保持与迁移？

这两个试验都不能仅比较使用 AI 时的练习分数。至少分开记录：即时正确率、无 AI 新题、延迟保持、错误模型出现率、提示依赖、用时和负荷。延迟可按课程设定，例如一周；该时长只是实施选择，不是最佳间隔结论。

评分可按每项 0/1/2 描述“错误/部分正确/正确且带条件”，维度包括准确性、关键关系、适用边界、表征一致性与新情境预测。它是待验证的评分规程，不是标准化量表。部分回答需人工双评；避免让同一个模型既提供内容又无依据地判满分。

对个人学习，可在多个相似难度知识点间交替使用两种配方，并记录延迟新题结果。这能帮助发现个人模式，但小样本、顺序和内容差异使其不能当成普适因果证据。

**真正的完成标准：学习者在减少帮助后，能重建目标关系、正确处理边界，并在新情境中作出有依据的判断。**

新增设计宜逐项比较：条件组合案例与单因素案例；显式信息核查与一般转换练习；变化矩阵与数量相同的常规例题；局部修复与重新完整讲解。控制总时间、基础任务难度与反馈机会，分别记录独立正确性、边界错误、错用/漏用原则、延迟表现及成本。不要一次同时改四项再把收益归给其中一项。

题目覆盖要与目标一致，预先写判据，并允许“信息不足且理由正确”得分。少量个人试用可以校正产品，但不能估计普遍效果；没有足够比较数据时，系统状态仍为设计综合。

## 16. 前沿与未知必须并列保留

本次未找到足够直接证据回答：复杂内容初学时粗模型是否普遍优于事实预问；六动作是否有统一最优顺序；每轮两三个操作是否最优；主因权重训练是否普遍改善迁移；哪种自适应策略能跨领域稳定胜出。

这些空白恰好是系统值得研究的地方，但不能用神经激活、理论合理性或 AI 的流利演示填补。神经与计算模型研究可以提出机制假说；对教学策略的选择，仍优先看真实学习行为和有合适对照的结果。

v2.0还没有直接解决：条件组合训练的跨领域增益；信息审计是否减少迁移错误且成本可接受；变化矩阵的最佳案例数与顺序；局部展开与返回的最佳时机；五维/十二项检查的评分可靠性。多来源理论相容不等于这些主张已经验证。

本次升级的确定成果是约束、任务与判据更明确，并纠正若干可能导致错误推断的表达；学习收益要由后续数据判断。

## 17. 证据台账：46项来源及其支持边界

访问范围是本文实际核查范围；“全文”指取得原文并查看相关段落，未表示重新审计所有原始数据。少数来源只核到作者摘要或原文检索段落，已逐条说明。在线发表年份与正式卷期年份不同处分别标注。

OS表沿用研究分类：A=元分析（对应E1），B=直接对照实验（对应E2），C=理论/叙述综合（对应H）；表中的限制优先于类型标签。RR中横断面与过程研究只用于识别困难，不作为教学策略因果依据。

### Orient / Scaffold：OS01—OS12


|ID|已核验原始来源与年份|研究类型 / 场景 / 对照|支持的核心结论|不支持的推断 / 访问范围|
|---|---|---|---|---|
|[OS01](https://link.springer.com/article/10.1007/s10648-023-09814-5)|Pan & Carpenter (2023), [Prequestioning and Pretesting Effects](https://link.springer.com/article/10.1007/s10648-023-09814-5)|C；综合词对、事实、文本、视频与课堂研究；预问+随后学习 vs 不预问学习|回答未知问题后有机会学习正确答案，可以促进相应内容记忆；机制和迁移边界仍待明确|不证明任意复杂 mental-model generation 都更好；全文开放并核阅，含记忆/迁移和机制段|
|[OS02](https://link.springer.com/article/10.3758/s13423-023-02353-8)|St. Hilaire, Chan & Ahn (2024；2023 在线), [Guessing as a learning intervention](https://link.springer.com/article/10.3758/s13423-023-02353-8)|A；预注册元分析；目标与非目标内容分开|特异效应 g=.54（97 个效应），一般效应 g=.04（91 个效应）|不能把 k 当作独立研究数；本次核到期刊摘要，全文付费，不报告未见方法细节|
|[OS03](https://link.springer.com/article/10.1007/s10648-025-10075-7)|King-Shepard et al. (2025), [The Effect of Prequestions on Learning: A Multilevel Meta-Analysis](https://link.springer.com/article/10.1007/s10648-025-10075-7)|A；多层元分析；预问题与未预问题信息|目标内容 g=.66，未预问内容 g=.01；加反馈的条件有更强目标收益|反馈调节不是反馈的独立随机因果效应；本次核到期刊摘要/注释，全文付费|
|[OS04](https://link.springer.com/article/10.3758/s13423-021-01904-1)|Brod (2021), [Predicting as a learning strategy](https://link.springer.com/article/10.3758/s13423-021-01904-1)|C，综述含 B；地理事实、比赛结果等简单陈述知识；预测 vs 事后报告|已有一定熟悉度时，先作预测可改变反馈加工；意外/注意是有实验和相关指标支持的解释|正文明确不涵盖复杂概念转变；瞳孔与后测关系不等于神经因果链；全文已核|
|[OS05](https://www.manyclasses.org/projects/many-classes-2/)|Motz et al. (2026 卷期；2025-08-28 在线), *ManyClasses 2*（DOI 10.1037/edu0000978）；[研究团队项目页](https://www.manyclasses.org/projects/many-classes-2/)|B；30 个真实课堂，n=1,571；个体内视频内容预问条件随机；延迟课程评估|目标题约提高 5 个百分点；同时部分学习者更可能跳过视频；已有知识与收益关联|不支持“学习量必增”或“模型激活已被证明”；团队原始介绍及作者上传论文全文已核；出版社 robots 阻断，团队页旧版仍写预印本，不要据旧标签称正式论文未发表|
|[OS06](https://journals.sagepub.com/doi/full/10.3102/00346543211019105)|Sinha & Kapur (2021), [When Problem Solving Followed by Instruction Works](https://journals.sagepub.com/doi/full/10.3102/00346543211019105)|A；53 项研究、166 次比较；PS-I vs I-PS；概念理解/迁移，实验和课堂准实验|平均 g=.36，95%CI [.20,.51]；高 PF 设计保真度关联更好结果，较低年级和领域通用技能有反向趋势|不能称“先自由探索普遍优于教学”；程序目标不保证优势；保真度亚组非独立因果；全文已核|
|[OS07](https://www.danamillercotto.com/uploads/4/7/7/2/47725475/barbieri_et_al__2023__we_meta-analysis.pdf)|Barbieri et al. (2023), [A Meta-analysis of the Worked Examples Effect on Mathematics Performance](https://link.springer.com/article/10.1007/s10648-023-09745-1)；[作者全文](https://www.danamillercotto.com/uploads/4/7/7/2/47725475/barbieri_et_al__2023__we_meta-analysis.pdf)|A；43 篇/55 研究/181 效应；小学至高教数学；例题学习 vs 常规解题等|总体 g=.48；多数研究在学校。正确范例、更少额外解释提示条件有更大效应|元回归不是因果；主要代数/几何，不能自动外推所有系统学习；作者全文已核，尤其调节限制段|
|[OS08](https://link.springer.com/article/10.1007/s10648-023-09817-2)|Sweller (2023), [The Development of Cognitive Load Theory](https://link.springer.com/article/10.1007/s10648-023-09817-2)|C；理论更新与实验传统；高/低元素交互、不同 expertise|复杂度取决于任务与已有 schema；熟练后原来多个元素能作为组块加工，某些指导效应减弱或逆转|元素交互不能仅由文本长度计算；无法精确读出个体工作记忆容量；不要把 CLT 解释当单一已证中介；全文已核|
|[OS09](https://maria-wirzberger.de/wp-content/uploads/2019/01/Rey2019_Article_AMeta-analysisOfTheSegmentingE.pdf)|Rey et al. (2019), [A Meta-analysis of the Segmenting Effect](https://link.springer.com/article/10.1007/s10648-018-9456-4)；[作者全文](https://maria-wirzberger.de/wp-content/uploads/2019/01/Rey2019_Article_AMeta-analysisOfTheSegmentingE.pdf)|A；56 项调查、88 比较；多媒体连续呈现 vs 连贯分段|记忆与迁移有小至中收益，整体认知负荷降低、学习时间增加；系统节奏也有收益|不支持越碎越好；保留因果连续性；本元分析的知识调节并非简单“新手获益最大”；全文已核|
|[OS10](https://www.cs.cmu.edu/~bmclaren/pubs/NajarMitrovicMcLaren-LearningWithITSAndWorkedExamples-UMUAI2016.pdf)|Najar, Mitrovic & McLaren (2016), [Learning with intelligent tutors and worked examples](https://www.cs.cmu.edu/~bmclaren/pubs/NajarMitrovicMcLaren-LearningWithITSAndWorkedExamples-UMUAI2016.pdf)|B；SQL tutor；固定例题/解题交替 vs 按所需帮助自适应选择完整例、渐隐例、解题|自适应条件学习更多；新手更快、较熟练者收获更大；指导量可随表现调整|不证明任意 LLM 可准确判断 schema，也不提供通用掌握阈值；作者机构全文已核|
|[OS11](https://www.annualreviews.org/content/journals/10.1146/annurev-psych-010416-044022)|Metcalfe (2017), [Learning from Errors](https://www.annualreviews.org/content/journals/10.1146/annurev-psych-010416-044022)|C；含实验传统；错误生成+纠正反馈，典型神经典型学习者|错误后正确反馈及错误推理分析能帮助学习；高信心错误不一定难改，存在 hypercorrection|不支持鼓励所有领域、所有人、所有高风险现场犯错；不能将短期纠正等同永久消除错误；期刊摘要/正文相关部分已核|
|[OS12](https://onlinelibrary.wiley.com/doi/full/10.1111/cogs.12086)|Renkl (2014), [Toward an Instructionally Oriented Theory of Example-Based Learning](https://onlinelibrary.wiley.com/doi/full/10.1111/cogs.12086)|C；范例学习研究综合；原则解释、子目标、选择解释、渐隐|把步骤编码为实现某子目标的有意义单元，比记固定链更适合灵活应用；指导应支持原则提取而非替代所有加工|不能把每条设计建议称独立元分析结论；全文已核|




### Differentiate / Instantiate：DI01—DI12


### DI01 — 案例比较的总体证据
Alfieri, Nokes-Malach & Schunn (2013), *Learning Through Case Comparisons: A Meta-Analytic Review*, Educational Psychologist. [已核原文PDF](https://scispace.com/pdf/learning-through-case-comparisons-a-meta-analytic-review-21w9vk760p.pdf)。57实验、336检验，混合实验室与课堂；检验层面摘要报告 d=.50。支持有指导的比较策略族，不能当每种配对方式的独立效应。原则呈现顺序等 meta 调节项是跨研究关联，不能当作普遍随机化顺序结论。核查：期刊/作者机构入口受阻，另打开原始论文PDF镜像核验。

### DI02 — 何时、比较什么、如何支持
Rittle-Johnson, Star & Durkin (2020), *How Can Cognitive-Science Research Help Improve Education? The Case of Comparing Multiple Strategies to Improve Mathematics Learning and Teaching*, Current Directions in Psychological Science, 29, 599–609. [期刊](https://journals.sagepub.com/doi/10.1177/0963721420969365)；[已打开的作者稿](https://cdn.vanderbilt.edu/t2-my/my-prd/wp-content/uploads/sites/3147/2021/01/Rittle-JohnsonStarDurkin2020_Current-Directions_CompareandExplain_Revision2.pdf)。综合数学课堂与实验研究。支持并排可见、角色对齐、针对性解释、按比较目的选例。低知识者的问题取决于材料数量、时间和支持，不是绝对禁止比较。叙述综述，不是新 meta。

### DI03 — 类比编码与实际互动任务
Gentner, Loewenstein & Thompson (2003), *Learning and Transfer: A General Role for Analogical Encoding*, Journal of Educational Psychology, 95, 393–408. [已打开的作者稿](https://groups.psych.northwestern.edu/gentner/papers/GentnerLoewensteinThompson03.pdf)。3研究，谈判策略新手；比较两案例优于分别学习，比较支持促进面对面谈判迁移。适合“角色—关系—共同策略”映射；不能证明任意故事类比或无限跨域迁移。

### DI04 — 受约束发明→讲解顺序
Schwartz, Chase, Oppezzo & Chin (2011), *Practicing Versus Inventing With Contrasting Cases: The Effects of Telling First on Learning and Transfer*, Journal of Educational Psychology. [已打开的 Stanford 稿](https://aaalab.stanford.edu/assets/papers/2011/Practicing_versus_inventing.pdf)。两个青少年物理实验，N=128、120；比较案例发明比例指标后再讲解，在深层结构与迁移优于先告知再练习，常规题表现接近。存在刻意设计的案例、任务约束和后续讲解；不能外推为新手自由发现优于讲解。

### DI05 — 交错学习有领域与相似性边界
Brunmair & Richter (2019), *Similarity Matters: A Meta-Analysis of Interleaved Learning and Its Moderators*, Psychological Bulletin, 145, 1029–1052. [PubMed](https://pubmed.ncbi.nlm.nih.gov/31556629/)；[已打开作者稿](https://www.uni-wuerzburg.de/fileadmin/06020400/2019/Brunmair_Richter_in_press__2019_META-ANALYSIS_OF_INTERLEAVED_LEARNING.pdf)。59研究、238效应量，总体 g=.42；绘画较强，数学较小，说明文本不明确，词语材料倾向 blocked。交错效应不能等同同时比较，也不等于间隔效应；材料与先验分类结构影响适用性。

### DI06 — 关系类别的反向结果
Steininger, Wittwer & Voss (2025；online 2024), *Learning Relational Categories: Benefits of Blocking, Classification, and Subject-Specific Examples*, Psychology Learning & Teaching, 24, 38–59. [已打开全文](https://journals.sagepub.com/doi/full/10.1177/14757257241248155)。师范生两实验，N=176、95；blocked 比 interleaved 更利于生成新例；分类任务优于只阅读；个人学科相关例有较小收益。优势主要见于例子生成，不是所有测验均获益；不能推为 blocked 全面优越。

### DI07 — 自适应配对辨别的新证据
Jacoby, Massey, Mettler & Kellman (2022；PMC上线2023), *Comparisons in Adaptive Perceptual Category Learning*, CogSci Proceedings, 44, 2372–2378. [已打开作者全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC10316997/)。N=75，学习22个人脸类别；配对辨别降低达到标准所需学习投入，测到新图片和一周测验。属于实验室知觉分类、会议论文；配对格式和反应选项数量同时改变，不能纯归因为关系抽象，更不能直接保证复杂概念学习收益。

### DI08 — 反驳文本的最新大范围 meta
Danielson et al. (2025；online 2024), *The Effectiveness of Refutation Text in Confronting Scientific Misconceptions: A Meta-Analysis*, Educational Psychologist, 60, 23–47. [作者机构摘要](https://experts.nau.edu/en/publications/the-effectiveness-of-refutation-text-in-confronting-scientific-mi/)。预注册 meta：71文章、76研究、111样本、294效应量；科学误概念纠正总体支持反驳文本。26调节项未显著解释差异，不等于所有条件相同。涵盖正式/非正式科学信息，不能把短期测验当作旧模型永久消除。核查：期刊检索与作者机构摘要，未完成全文审核。

### DI09 — 多样性：维度×阶段，而非越多越好
Raviv, Lupyan & Green (2022), *How Variability Shapes Learning and Generalization*, Trends in Cognitive Sciences, 26, 462–483. [作者机构页](https://eprints.gla.ac.uk/272070/)；[已打开作者稿](https://eprints.gla.ac.uk/272070/2/272070.pdf)。跨类别、语言、运动技能的理论整合。变异与泛化的关系依赖变化维度和学习阶段，训练变慢可能伴随迁移改善。相同变异何时引入的直接比较仍少；不能据此规定每次三个例子、每轮增加固定差异。

### DI10 — fading 的明确理论，不等于普遍验证
Fyfe & Nathan (2019；online2018), *Making “Concreteness Fading” More Concrete as a Theory of Instruction for Promoting Transfer*, Educational Review, 71, 403–422. [期刊](https://www.tandfonline.com/doi/abs/10.1080/00131911.2018.1424116)；[已打开机构稿](https://scholarworks.iu.edu/dspace/bitstreams/2c814639-f4c7-4091-a6eb-5e6e834bc546/download)。理论澄清具体动作→图像→抽象记号以及显式联系；作者提出可检验预测。不是足以支持所有年龄/学科的 meta。

### DI11 — 不同学科的具体性含义不同
Kokkonen & Schalk (2021；online2020), *One Instructional Sequence Fits All? A Conceptual Analysis of the Applicability of Concreteness Fading in Mathematics, Physics, Chemistry, and Biology Education*, Educational Psychology Review, 33, 797–821. [已打开全文](https://link.springer.com/article/10.1007/s10648-020-09581-7)。概念分析：具体材料是否激活相关先验知识、各表示的功能和领域学习目标必须区分。不能把数学符号习得逻辑直接套进物理机制学习；非实验性因果证据。

### DI12 — 高中复杂物理的无优势结果
Kokkonen, Lichtenberger & Schalk (2022；DOI含2021), *Concreteness Fading in Learning Secondary School Physics Concepts*, Learning and Instruction, 77, 101524. [作者机构记录与原文入口](https://researchportal.helsinki.fi/en/publications/concreteness-fading-in-learning-secondary-school-physics-concepts/)。课堂实验N=70，电磁感应，实物/场线图/形式数学；fading与反向均有效，无总体优势。无延迟测验等限制；支持“未证实通用顺序”，不是证明所有顺序等效。核查：期刊检索返回方法与结果原文段；作者机构记录已打开，PDF入口本次受阻。


### Relate / Re-represent：RR01—RR12


|ID|原始来源、年份、已核查URL|设计/场景|可支持的最小论断|边界与访问级别|
|---|---|---|---|---|
|[RR01](https://link.springer.com/article/10.1007/s10648-018-9434-x)|Bisra, Liu, Nesbit, Salimi & Winne (2018), *Inducing Self-Explanation: a Meta-Analysis*, Educational Psychology Review. [原文/机构记录](https://link.springer.com/article/10.1007/s10648-018-9434-x) |64研究报告、69效应；阅读、例题、解题等多情境|提示自解释的总体加权 g=.55；研究定义强调因果/概念推断|策略家族证据，不能给20种微提示各自赋 g=.55；只核查出版方摘要与参考文献|
|[RR02](https://rex.libraries.wsu.edu/esploro/outputs/journalArticle/Studying-and-Constructing-Concept-Maps-a/99900601155801842)|Schroeder, Nesbit, Anguiano & Adesope (2018), *Studying and Constructing Concept Maps: a Meta-Analysis*. [原文/机构记录](https://rex.libraries.wsu.edu/esploro/outputs/journalArticle/Studying-and-Constructing-Concept-Maps-a/99900601155801842) （DOI 10.1007/s10648-017-9403-9）|142独立效应，N=11,814；STEM及非STEM|节点—带标签关系图总体 g=.58；建图相关收益大于读图的各自对照收益|g=.72 对 .43 是调节比较，不是充分控制的统一头对头比较；不能把装饰性思维导图当概念图；作者机构摘要|
|[RR03](https://link.springer.com/article/10.1007/s10648-025-10067-7)|Leutner & Biele (2025), *Without Integration, Everything Is Nothing: A Meta-Analysis of the Effectiveness of Instructional Support for Drawing-to-Learn*. [原文/机构记录](https://link.springer.com/article/10.1007/s10648-025-10067-7) |14研究、16独立比较、N=1,213；有/无绘图支持|整体额外支持无显著收益；促进整合支持的理解效应 g=.35；一般支持不保证迁移|小研究数、异质性；机制分类为调节分析，非中介因果证明；出版方开放全文|
|[RR04](https://link.springer.com/article/10.1007/s10648-024-09871-4)|Kobayashi (2024), *Interactive Learning Effects of Preparing to Teach and Teaching: a Meta-Analytic Approach*. [原文/机构记录](https://link.springer.com/article/10.1007/s10648-024-09871-4) |39研究；教学预期×随后教学；知识学习|总体 g=.27；先有教学预期 g=.48，无预期 g=-.02；另14研究显示实际教超过仅准备 g=.38|勿把零附近效应写成证明无效；无需进一步叠加“教AI优于教人”等未测结论；出版方摘要|
|[RR05](https://languageandlearninglab.com/wp-content/uploads/1-s2.0-S0022096522000959-main.pdf)|Nyhout & Ganea (2022), *Learning science concepts through prompts to consider alternative possible worlds*, Journal of Experimental Child Psychology 222, 105466. [原文/机构记录](https://languageandlearninglab.com/wp-content/uploads/1-s2.0-S0022096522000959-main.pdf) |6–7岁行星宜居教学实验；Study1 N=102，Study2 N=70|反事实与替代例子均有学习/迁移；Study1 反事实有部分额外迁移收益，Study2 两者相当|不支持反事实稳定优于多实例；对照未接受教程，不能把所有教程收益归于反事实；作者实验室全文|
|[RR06](https://link.springer.com/article/10.1007/s11251-008-9051-z)|Berthold, Eysink & Renkl (2009；online 2008), *Assisting self-explanation prompts are more effective than open prompts when learning with multiple representations*. [原文/机构记录](https://link.springer.com/article/10.1007/s11251-008-9051-z) |N=62 概率论多表征例题；辅助解释/开放解释/无提示|两种提示促进程序知识；辅助提示更有利于概念知识，适合填缺口而非全自由生成|单一概率学习实验，不证明所有领域辅助均更好；出版方摘要|
|[RR07](https://link.springer.com/article/10.1007/s10648-024-09958-y)|Rexigel, Kuhn, Becker & Malone (2024), *The More the Better? A Systematic Review and Meta-Analysis of the Benefits of More than Two External Representations in STEM Education*. [原文/机构记录](https://link.springer.com/article/10.1007/s10648-024-09958-y) |46研究综述；23研究进入数量比较meta，132效应|>2表征相对2表征成绩原合并 g=.258，剔除25个潜在离群效应后的估计 g=.118；适当支持调节收益|表征配置≠翻译行为；不能推导越多越好或固定排序；出版方开放全文|
|[RR08](https://cicl.stanford.edu/papers/gong2023active.pdf)|Gong, Gerstenberg, Mayrhofer & Bramley (2023), *Active causal structure learning in continuous time*, Cognitive Psychology 140, 101542. [原文/机构记录](https://cicl.stanford.edu/papers/gong2023active.pdf) |2个人类主动因果装置实验，含循环结构|干预取得证据的质量及复杂度与学习准确性相关；人们选择较简单但有信息的因果动态|实验室因果结构学习，不是常规课堂反事实提示试验；结果包括行为与模型拟合，不能全解释为训练因果效应；作者实验室全文|
|[RR09](https://academic.oup.com/chidev/article/88/1/229/8257898)|Walker, Lombrozo, Williams, Rafferty & Gopnik (2017), *Explaining Constrains Causal Learning in Childhood*. [原文/机构记录](https://academic.oup.com/chidev/article/88/1/229/8257898) （DOI 10.1111/cdev.12590）|三实验，5岁儿童 N=114；解释 vs 报告观察|解释会改变假设选择，偏向覆盖面或符合既有知识的解释；冲突时先验可占优|解释能定向选择，不保证更正确；不是成人STEM误概念纠正的普适证明；出版方全文|
|[RR10](https://link.springer.com/article/10.1007/s12564-011-9187-4)|Cho & Jonassen (2012；online 2011), *Learning by self-explaining causal diagrams in high-school biology*. [原文/机构记录](https://link.springer.com/article/10.1007/s12564-011-9187-4) |63韩国高中生随机三组；因果图理解|自解释与读解释相当；把自解释与规范解释比较的元层反馈增强效果|小样本特定生物领域；一侧推理、错误解释、缺推论是实际难点；出版方摘要|
|[RR11](https://onlinelibrary.wiley.com/doi/10.1002/sce.70066)|Molad & Haskel-Ittah (2026), *Learning Trajectories for Constructing Mechanistic Explanations and the Role Played by Epistemic Knowledge*. [原文/机构记录](https://onlinelibrary.wiley.com/doi/10.1002/sce.70066) |65名10–11年级学生、4个生物班；晒黑机制黑箱选择的过程研究|机制学习会选择不同的待展开黑箱与路径；解释完整性判断可作为设计关注点|非随机训练效果研究；作者明确未分析最终解释优劣；摘要写3类而讨论含随机共4类，不引用类数；开放全文|
|[RR12](https://pmc.ncbi.nlm.nih.gov/articles/PMC9582828/)|Kiesewetter & Schmiemann (2022), *Understanding Homeostatic Regulation: The Role of Relationships and Conditions in Feedback Loop Reasoning*, CBE—Life Sciences Education. [原文/机构记录](https://pmc.ncbi.nlm.nih.gov/articles/PMC9582828/) |高中/本科生横断面测量；血钙调节系统|间接关系、反向初始条件会增加反馈推理难度|作者只是提出教学可能受益；非教学干预，不能称已证实训练效果；开放全文|


## 前沿设计与方法论来源 F01—F08

| ID | 原始来源 | 类型、环境与核查范围 | 最小结论与限制 |
|---|---|---|---|
| [F01](https://link.springer.com/article/10.1007/s10648-023-09769-7) | Fiorella (2023), *Making Sense of Generative Learning*. [期刊全文](https://link.springer.com/article/10.1007/s10648-023-09769-7) | 理论与叙述性综合；跨学习活动；开放全文 | 区分解释、可视化、动作三类意义建构；提供指导程度框架。不是每种任务或序列的独立因果检验。 |
| [F02](https://www.researchgate.net/publication/391489104_Scaffolding_through_prompts_in_digital_learning_A_systematic_review_and_meta-analysis_of_effectiveness_on_learning_achievement) | Thomann & Deutscher (2025), *Scaffolding through prompts in digital learning: A systematic review and meta-analysis of effectiveness on learning achievement*. [作者上传的论文摘要](https://www.researchgate.net/publication/391489104_Scaffolding_through_prompts_in_digital_learning_A_systematic_review_and_meta-analysis_of_effectiveness_on_learning_achievement) | 68项数字学习提示实验；期刊摘要与作者上传页面核查，未完成全文方法复核；DOI 10.1016/j.edurev.2025.100686 | 总体 d=.394、偏倚校正估计 .220；不能用跨研究调节给某一现代 LLM 提示排序。 |
| [F03](https://link.springer.com/article/10.1007/s10648-026-10164-1) | Breitwieser et al. (2026), *Digital Prompting in Education: A Design Framework and Bibliometric Analysis*. [期刊全文](https://link.springer.com/article/10.1007/s10648-026-10164-1) | 文献计量与概念框架，1,238篇；2026-05-04发表；开放全文 | 将提示视为动态支架；它整理设计维度，未独立验证每种实时调度策略。 |
| [F04](https://link.springer.com/article/10.1007/s10648-025-10039-x) | Makransky et al. (2025), *Beyond the “Wow” Factor: Using Generative AI for Increasing Generative Sense-Making*. [期刊全文](https://link.springer.com/article/10.1007/s10648-025-10039-x) | 175名大学生与234名高中生，两项真实课堂实验；开放全文，复核结果段 | 支持把生成任务和反馈嵌入Tutor，但结果随对照与测量时间改变。高中延迟为1—2周，大学4周，不能合称全部4周；摘要与正文显著性表述有不一致，按结果段保守报告。 |
| [F05](https://doi.org/10.1073/pnas.2422633122) | Bastani et al. (2025), *Generative AI without guardrails can harm learning: Evidence from high school mathematics*. [期刊全文](https://doi.org/10.1073/pnas.2422633122) | 土耳其高中数学现场随机实验；期刊全文关键结果已核 | GPT Base练习期更好，撤去后相对对照低约17%；GPT Tutor消除了明显不利，独立考试未显著优于对照。不能把整套设计的结果归于单个提示。 |
| [F06](https://www.nature.com/articles/s41598-025-97652-6) | Kestin et al. (2025), *AI tutoring outperforms in-class active learning: an RCT introducing a novel research-based design in an authentic educational setting*. [原文](https://www.nature.com/articles/s41598-025-97652-6) | 大学物理N=194，交叉随机，两节内容；原文检索返回的方法及结果核查 | 特定精心设计Tutor有即时优势；不足以证明长期保持、远迁移或所有普通AI聊天的效果。 |
| [F07](https://link.springer.com/article/10.1007/s10648-026-10210-y) | Cho (2026), *Relocating the Locus of Generation: The AI-GLM Framework for Generative Learning in AI-Mediated Mathematics Education*. [期刊全文](https://link.springer.com/article/10.1007/s10648-026-10210-y) | 2026-08-18发表；理论分析，非系统综述或实验；全文 | 对AI角色与认知劳动归属提供设计视角；框架及其命题有待检验，不是验证完成的最优策略。 |
| [F08](https://education.asu.edu/sites/g/files/litvpz656/files/lcl/chiwylie2014icap_2.pdf) | Chi & Wylie (2014), *The ICAP Framework: Linking Cognitive Engagement to Active Learning Outcomes*. [作者机构全文](https://education.asu.edu/sites/g/files/litvpz656/files/lcl/chiwylie2014icap_2.pdf) | 理论与实证综合；实验室及课堂；PDF全文 | 外显活动可作为认知参与的代理；ICAP参与层次不能直接当作本文八级“内容深度”理论，也不能仅从聊天轮次断言交互建构。 |

以上均用于限定设计判断。效应量的对照条件、测量时间和材料不同，不按数值大小给策略排总榜。


### 本次升级补充：U01—U02

| ID | 来源与核验范围 | 支持的设计判断 | 不能据此宣称 |
|---|---|---|---|
| [U01](https://www.researchgate.net/profile/Shaaron-Ainsworth/publication/222410911_DeFT_A_conceptual_framework_for_learning_with_multiple_representations_Learning_and_Instruction_16_183-198/links/5ea69ecb45851553fab2dd69/DeFT-A-conceptual-framework-for-learning-with-multiple-representations-Learning-and-Instruction-16-183-198.pdf) | Ainsworth (2006), *DeFT: A conceptual framework for considering learning with multiple representations*. Learning and Instruction, 16(3), 183–198. DOI: 10.1016/j.learninstruc.2006.03.001。已打开作者预发表全文，2026-09-24核验。 | 区分表征设计、功能与学习者任务；允许互补信息，注意转换成本。框架性依据，按H使用。 | 新增信息审计、冲突检查及具体中文问法已被逐项验证；多表征总比单表征好。 |
| [U02](https://pdf.retrievalpractice.org/transfer/Barnett_Ceci_2002.pdf) | Barnett & Ceci (2002), *When and Where Do We Apply What We Learn? A Taxonomy for Far Transfer*. Psychological Bulletin, 128(4), 612–637. DOI: 10.1037/0033-2909.128.4.612。已打开原论文全文，2026-09-24核验。 | 迁移沿多维描述，不能混成单一远迁移量。该文提出9维分类；本系统变化记录是任务化改编，按H使用。 | 本报告五条轴、十二项检查或四格教学方案来自该文的已验证量表；论文规定了最优训练序列。 |

本次为针对升级主张的补充核查；新增两项经典来源，复核[DI09](https://eprints.gla.ac.uk/272070/2/272070.pdf)、[OS08](https://link.springer.com/article/10.1007/s10648-023-09817-2)、[RR08](https://cicl.stanford.edu/papers/gong2023active.pdf)等关键依据，保留原44项来源及原核验限制。没有把旧综述包装成新实验，也没有重新执行穷尽性系统检索。
