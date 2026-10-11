# Agent 与 Skill 系统：验收目标替代与指令负担审计

日期：2026-10-11，Asia/Shanghai。审核对象是项目内四个逻辑 Agent、七个 Skill、人工学习入口、关键引用与策略资源，以及 RSSM、Flow Matching、最近 WM／KV Cache 备课和一段真实 M0 学习记录。采用 BitterPillEngineering 的重复、冲突、历史补丁、按需读取与 HOW／WHAT 检查，并由三个子 Agent 分别检查源规则、产物、验证机制。子 Agent 继承本次审计背景，是分工核查，不是盲评或受控实验。

**判断：用户担忧有具体依据。已出现过“系统自选一个较窄目标，再围绕它完成专业检查，最终可采用，但较宽认识用途仍不充分”的现象。现行规则还存在明显的运行读取负担。证据不足以认定系统全面失去能力，也不足以认定规则数量已经造成了可测的推理能力下降。**

最值得纠正的是完成标准和注意力分配：让学科问题、关键机制、认识上的困难与教学转换决定工作；让验收负责发现具体错误和用途缺口。检查通过不能单独成为质量结论。另一方面，达到原用途所需程度、没有有价值增量时结束仍然合理，不能把纠偏变成无限研究。

本次只新增这份审计，未修改 Agent、Skill、资源、契约或学习历史。原先已有未提交的 WM 审核、KV 备课及课程索引变动保持原样。未重新运行工程测试，也未发起新的备课对照实验。

**已核实的现象与推断边界**

| 项目 | 判断 | 依据强度 |
|---|---|---|
| 自选目标形成自证闭环 | 历史实例支持，值得优先处理 | 有具体目标、材料与审查的观察链；因果贡献未测 |
| 当前入口与资源读取负担 | 明确存在可压缩载荷 | 文件内容与字符统计；不是实际 token 或耗时测量 |
| 大量检查挤占学科推理 | 合理风险，尚未证明程度 | 缺同模型、同任务、同预算的规则消融对照 |
| 全面只求形式、专业内容贫乏 | 当前证据不支持 | 最新产物已有机制推导、条件变化与实质回修 |
| 已产生真实学习增益 | 不能由备课审查推出 | 近期主要是备课；真实 M0 记录仍显示教学转换困难 |

**1．最强问题是自选目标的闭环**

[RSSM 复盘](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/reviews/2026-10-09-rssm-system-root-cause-analysis.md:17)记录的传递链是：宽主题与深度备课请求 → 选定给定模型的推导／审计目标 → 固定 toy → 做细参考与数值检查 → 修错、限定用途后接受 → 结构取舍、参数学习和决策意义没有同等展开。

具体的 A03 已被审查发现：所有行动的未来方差相同，方差影响绝对成本却不改变排序。限定该例的用途可以保留它的正确性，但不能因此认为“不确定性怎样影响决策”已经被充分展示。原报告也说明这是系统建议目标的选择问题，不能把它说成已约定的神经实现目标被偷偷降低。见[用途分析](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/reviews/2026-10-09-rssm-system-root-cause-analysis.md:48)、[A03](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/reviews/2026-10-09-rssm-system-root-cause-analysis.md:62)。

[Flow Matching 深度复查](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/reviews/2026-10-10-flow-matching-relation-depth-review.md:9)也区分了“原桥接有采用资格”与“用户希望的深入理解仍不充分”。给定结构内重建较强，改变结构后的联动、歧义诊断和方法构造较弱。见[具体覆盖差异](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/reviews/2026-10-10-flow-matching-relation-depth-review.md:73)。

这说明多个角色各自把同一窄目标完成，并不能保证有人重新判断目标是否抓住原用途。增加 Agent 数量不直接解决这个问题。该解释有观察依据，[原复盘明确没有受控因果验证](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/reviews/2026-10-09-rssm-system-root-cause-analysis.md:175)。

“范围有限”“暂缓”“未知”是必要的事实表达。它们也可能成为容易完成的出口：如果漏掉的是用途必需的关系，应补实质内容或说明当前交付尚未满足；只有有理由的阶段取舍，才可以据有限范围完成当前工作。不能用限定措辞自动消除原用途的缺口。

**2．当前规则已在防止这个问题，应保留其核心**

2026-10-10／11 的修订要求先检查系统建议目标是否承接原用途，再检查任务是否满足目标；AG2 先研究专业问题、机制、替代与条件，AG3 从原用途建立问题后检查成品。

- [goal-design:32](E:/文献资料/学习系统架构设计/personal-learning-suite/src/skills/learning-goals/references/goal-design.md:32)明确禁止先缩成容易验收的目标，再据题目满足它认定用途已覆盖。
- [AG2:15](E:/文献资料/学习系统架构设计/personal-learning-suite/src/agents/AG2-materials.md:15)要求交出有内容的专业研究，不能只验设计者答案。
- [SK03:23](E:/文献资料/学习系统架构设计/personal-learning-suite/src/skills/learning-teaching/SKILL.md:23)明确完整文件、卡片调用、正确教师答案不能代证教学充分。
- [反向审查:38](E:/文献资料/学习系统架构设计/personal-learning-suite/src/skills/learning-teaching/references/disciplinary-to-teaching.md:38)回查原用途、专业关系、实际输入和学习者工作。

这些保护有实际价值。“先取得可靠学科依据，再进行教学转换”也有必要的依赖关系，不能因为它规定了顺序就一律删除。BitterPillEngineering 的“HOW 候选删减”与“验收工具优先保留”都只作为检查视角；本审计同时检查程序编排和验收本身是否服务任务，不预设规则越少越好。

**3．最新产物确实在做专业分析和认识设计**

WM r1 的[可见材料](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/questions/visible/decision-sufficient-preparation-r1/materials.md:72)连接观测 MSE、候选排序和真实奖励；用同输入必须对应不同输出的冲突解释为什么继续优化无法修复表示缺失；另有受限价值等价与函数集合闭合的反例。T2 留下新评价条件下的判断，T5 留下竞争原因、实验选择和不同结果的解释。

KV 的[可见材料](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/questions/preparation-tests/transformer-kv-cache-20261011/visible/04-materials.md:38)从因果可见范围推到逐层旧状态不变，再说明新 Query 仍需重新计算权重。[反向审查](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/artifacts/lesson-preparation/2026-10-11-transformer-kv-cache-r1/07-reverse-review.md:83)把原先只在参考中的累计成本放回任务，补实际日志并修时间线分支误导。这些回修改变了教学内容。

也不能把同主题的新版一律视为更深。旧 WM [材料:118](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/artifacts/preparation-tests/2026-10-10-decision-sufficient/03-learner-materials.md:118)有数据→损失→梯度→参数→后继→评分→动作微轨迹，r1 [材料:164](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/questions/visible/decision-sufficient-preparation-r1/materials.md:164)主要保留训练作用的文字概括。r1 明确选用模型选用、修正与验证的[纸面技术判断用途](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/artifacts/lesson-preparation/2026-10-11-decision-sufficient-r1/03-cognitive-design.md:7)。当前范围记录没有保存原用户逐字要求，不能据旧版更详断定新版违令；可以确定，r1 通过不能外推为“世界模型怎样学出来”的完整深入教学已完成。

真实 M0 记录则显示了另一种故障：[用户求助原话](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/sessions/2026-10-07-01/raw/M0-feature-sequence-001-help-request.txt:1)表明恢复依据、两条路线和帧身份没有变成可理解的输入；[事件记录](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/sessions/2026-10-07-01/event-M0-feature-sequence-001.md:8)保留局部正确并将后续判断保持未裁定。这证明教学转换不足确实发生过，但没有证明系统为验收而伪报掌握。

**4．运行读取负担有明确热点**

实际加载路径是 AGENTS → control/current → MODEL_ENTRY → FRAMEWORK 指向共享契约、SK00、AG0、session-entry → 当前专业规则。入口明确禁止同次循环重读及每轮预载全部研究，所以全仓库文件数、39 份 Skill Markdown 或 64 个策略包不能算成每次输入。

以下字符数来自本次文件原文统计，包含换行等字符，不是 tokenizer 统计。静态首接路径合计 38,645 字符，尚不含状态、课程和专业规则；START_PROMPT 是另行复制的用户启动文本，不计入该合计。

| 静态首接文件 | 字符数 |
|---|---:|
| AGENTS.md | 994 |
| MODEL_ENTRY.md | 4,440 |
| FRAMEWORK.md | 5,994 |
| contracts/shared-contracts.md | 17,447 |
| personal-learning/SKILL.md | 2,675 |
| AG0-coach.md | 2,894 |
| session-entry.md | 4,201 |
| 合计 | 38,645 |

共享契约承担共同语义、22 类对象字段、运行表示、B2a 兼容、授权绑定、SQLite 提交和静态 JSON 表，人工入口却纳入首接阅读。见[对象表](E:/文献资料/学习系统架构设计/personal-learning-suite/contracts/shared-contracts.md:23)、[兼容与运行细节](E:/文献资料/学习系统架构设计/personal-learning-suite/contracts/shared-contracts.md:48)、[静态表](E:/文献资料/学习系统架构设计/personal-learning-suite/contracts/shared-contracts.md:105)。其“WorkOrder／WorkResult 或同字段视图”与简单任务不填完整表单并不直接矛盾，但可能诱导模型在自然语言中仍追求全面字段覆盖。

另一热点是[选法规则:43](E:/文献资料/学习系统架构设计/personal-learning-suite/src/skills/learning-strategies/references/selection-adaptation.md:43)：读取完整 JSON、Encoding 两载体全文，Post 还读完整源段和证据条目。本次统计 S05 包 19,252 字符、Post/select-method 34,478 字符。包内有操作正文，也有重复共用规则、来源正文、研究片段和大量定位元数据。索引全文 149,707 字符，但规则只要求核对相应候选，不能断言每次读全索引。现行[:51](E:/文献资料/学习系统架构设计/personal-learning-suite/src/skills/learning-strategies/references/selection-adaptation.md:51)已允许复用同版本共用内容。

这些数据能证明输入载荷和可精简位置，不能测出多少注意力被浪费。系统有空间继续推理也不等于这些载荷无成本；是否影响当前模型的专业质量仍需对照。

**5．验收指标的范围基本诚实，汇报重心需要改变**

[check_release.py:73](E:/文献资料/学习系统架构设计/personal-learning-suite/validation/disciplinary-workflow-2026-10-11/check_release.py:73)的 pass 主要由保护文件、manifest、缺文档及断链决定，脚本明确不检学科正确性或学习效果。这些检查负责工程可靠性，不能回答是否形成了有解释力的专业认识。[B7 覆盖脚本](E:/文献资料/学习系统架构设计/personal-learning-suite/scripts/check_b7_coverage.py:97)也把完整行为与真实 V1—V4 保留未执行。

因此，指纹、格式和测试通过不应占据主要质量结论。汇报应先说明：解释了哪条关键关系；哪种条件变化会改变判断；成品怎样支持这种理解或工作；仍缺哪项必要认识。工程检查可以作为附属结果。用几十项有限数值检查验证合法例子有价值，增加检查项数却不自动增加理解覆盖。

当前系统也没有普遍伪装独立性。[多 Agent 流程复查](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/reviews/2026-10-09-multiagent-vs-single-workflow-review.md:24)交代继承上下文，最新[行为复核](E:/文献资料/学习系统架构设计/personal-learning-suite/validation/disciplinary-workflow-2026-10-11/behavior-review.md:18)交代先定问题后看成品的范围；[:14](E:/文献资料/学习系统架构设计/personal-learning-suite/validation/disciplinary-workflow-2026-10-11/behavior-review.md:14)确实拒绝了自定小目标满足即整体覆盖的判断。还有[失败重放](E:/文献资料/学习系统架构设计/personal-learning-suite/validation/teaching-content-phase6-2026-10-05/failure-replays.md:9)只修输出、没有再叠规则的例子。

**建议的精简顺序**

| BPE 分类 | 具体处理 | 需要保留的能力 |
|---|---|---|
| MERGE | AGENTS／MODEL_ENTRY／FRAMEWORK／启动词保留路径和触发，学科协作与主线准备集中维护 | 角色责任、实际用途、连续教学和恢复 |
| MOVE | 从共享契约生成短的人工运行视图；完整对象表、synthetic 兼容、提交与绑定按程序调用或维护读取 | 原答、帮助、来源、条件、控制和可恢复事实；技术契约仍保留 |
| MERGE／MOVE | 策略生成单一运行正文，完整双载体和研究档案按争议／溯源读取；索引提供候选短视图 | 目的、前置、必要操作、风险、反馈、停止／返回及重要证据限制 |
| EVALUATE | 保留本次连贯主线，压缩固定角色编排和全面准备；按关键关系扩大工作 | 学科依据、解释桥梁、完整任务的承重连接，避免临时一道题代替单元 |
| EVALUATE | 重新检查普通反馈前“必须写盘并读回”的强依赖 | 可靠捕获原答，失败不称已保存，重要复核与恢复取得可回查原件 |
| KEEP | 专业正确性、合法多解、用户控制、AI／用户贡献、备课／表现／收益的区分 | 避免用释放能力换取错误、伪造或用户控制丢失 |

反馈延迟这一项应单独试改：[INTERACTION:3](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/INTERACTION.md:3)已有用户每答后等待数分钟、容易分心的记录；[:9](E:/文献资料/学习系统架构设计/learning/embodied-intelligence/INTERACTION.md:9)仍要求反馈前必要保存读回。可以研究普通反馈在可靠捕获后及时交付、集中持久保存的路径，重要评价与恢复仍依赖原件。现有记录没有隔离耗时原因，不能直接把数分钟归因于该规则；当前规则尚未改变，也不能虚称后台会自动保存。

不建议新增一个“防腐败 Agent”、更多表单、固定深度分数或一套新的会签流程。现有 AG2／AG1／SK03／AG3 足以承担工作；需要改变它们的读取内容、判断依据与交付重心。识别一次输出错误后，若原规则已足够，优先修材料、解释或实例，不再添加同义禁令。开放专业探索中，研究可以校准系统建议的目标，发现用途相关的新问题；不能把未能预先写成判据的重要关系机械归为范围外。

**可供对照的精简核心草案，尚未生效**

> 围绕用户希望理解或完成的实际工作，研究当前专业对象、关键关系、机制、条件和必要依据。把重要认识转换成可靠、可理解的解释与工作；需要学习者贡献时保留实质判断，纯解释直接交付。允许研究修正系统建议的目标和表示，明确有理由的阶段取舍。按实际内容选择方法和形式，已有充分材料直接复用。专业审查从原用途查必要连接、重大错误和实际成品，发现问题只修相关位置。保留用户控制、来源与贡献事实及必要恢复记录；维护字段、完整溯源和程序流程按需要加载。满足本次用途、没有值得继续的缺口或预算结束时收束，如实说明完成和限制。

该草案表达目标和底线，不作为新的巨大检查表，也没有替代真实课程的控制状态和既有授权。

**最小区分实验，尚未执行**

选一个未备课的主题，保持同一模型、推理设置、资料、实际用户用途、预算和交付范围。两个新上下文分别用现行规则和精简规则，各产出同样范围的解释、材料与工作。精简版保留专业正确性、用户控制、贡献与事实底线，减少重复入口、维护技术载荷和无关流程。两边都不能预看旧成品。

审阅者先从原用途和资料提出少量关键专业关系，再看匿名产物，比较机制解释、条件改变后的联动、学习者剩余工作、重大错误，以及实际时间／token；不按文件数、篇幅、检查项数评分。先做一对，有具体差异再配对复现，不先搭评估平台。

若精简版反复更深入且更省，支持过度规则负担解释；若两边都窄，更应定位领域分析、目标选择或材料转换；若完整规则更强，应该保留有用约束。这个实验检验备课能力，真实学习效果仍需另有学习者证据。

外部研究只能支持风险意识：[Lost in the Middle](https://aclanthology.org/2024.tacl-1.9/)在当时模型与检索／问答任务中发现长上下文利用受相关内容位置影响；不能直接证明本系统当前模型因规则变弱。[FollowBench](https://aclanthology.org/2024.acl-long.257/)把约束遵循与纯回答质量分开考察，也提醒我们不能用合规替代内容质量。两者都没有测试本仓库当前教学流程。

本审计建议先精简运行层、让专业建设主导交付，再用小对照决定继续删什么。专业核验保留相称范围，停止条件回到实际用途；“可验收”不再单独承担“已经充分发挥能力”的结论。
