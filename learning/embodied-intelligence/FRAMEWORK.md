# 共享框架路由

维护源在项目根的 personal-learning-suite；本学习目录引用当前 Agent／Skill 指导，不维护另一份专业规则。更换模型先读同一入口和真实记录，再按需读当前规则。移动整个项目时相对路径保持可用；只复制本目录须补齐所依赖框架。

人工文件模式见 [MODEL_ENTRY](MODEL_ENTRY.md)，总入口为 [SK00](../../personal-learning-suite/src/skills/personal-learning/SKILL.md)及 [开始／恢复](../../personal-learning-suite/src/skills/personal-learning/references/session-entry.md)。这里的真实记录不导入虚构 SQLite；程序 API 和分期开发状态仅在实际调试／调用时读取。无原生 Skill 发现时，模型仍可读取文件执行指导，不宣称已安装或绑定宿主。缺读取能力说明缺项与可用范围。

当前框架的来源比较和新上下文虚构首回合见 [全套原意复审](../../docs/audits/AI个人学习系统_全套Skill与Agent原意复审_2026-10-05.md)。这些审查者是维护任务的子 Agent，不代表本学习目录已经启动四个独立教学模型，也不增加任何个人学习表现。

## 最少使用路径

| 当前情境 | 读取与工作 |
|---|---|
| 开始／继续 | 尚未取得的 AGENTS、当前控制／状态、MODEL_ENTRY → 共享契约、SK00 session-entry、AG0 → 当前引用与必要专业规则；同次已读不循环加载 |
| 新单元没备好 | SK03内容准备、Encoding、Post功能与SK06选法；SK01明确认知目标，SK02核材料，SK05接近期整体；实际读所选完整策略，备主要路径后展示，旧范例／一题不算已备单元 |
| 活动已适用／作品已存在 | 直接 SK03 执行，或 SK04 按原件与条件检查；不遍历全部角色 |
| 复习／应用 | Post 功能分流；必要局部 Encoding 后回父任务，选法有差异才 SK06 |
| 单元整体收束／重要跳过／关键未完成取舍 | AG3职责与SK04整体评审，按原答和帮助分项核对；AG1接同一作品的下一可执行工作，AG0呈现，允许同模型兼任，不要求四独立Agent |
| 解释安排、换形式、跳过检查、缩时、争议、换模型 | SK00 相应控制／恢复分支，再按需读计划／专业复核；用户可看完整依据并转教学，形式就是目标时保留未覆盖要求 |

四角色表示决定责任。当前模型可顺序兼任相容职责，普通反馈无需全员会签；必要的重要复核仍需足够能力及依据，不能以换角色代替独立性。默认不自动发起子 Agent 或后台工作。

## 四角色

| 角色 | 原始定义 | 用途 |
|---|---|---|
| AG0 | [AG0-coach.md](../../personal-learning-suite/src/agents/AG0-coach.md) | 会话执行、真实过程与恢复 |
| AG1 | [AG1-design-planning.md](../../personal-learning-suite/src/agents/AG1-design-planning.md) | 目标、设计与计划 |
| AG2 | [AG2-materials.md](../../personal-learning-suite/src/agents/AG2-materials.md) | 内容与材料核验 |
| AG3 | [AG3-assessment.md](../../personal-learning-suite/src/agents/AG3-assessment.md) | 证据评价与复核 |

## 七 Skill

| Skill | 原始入口 | 何时加载 |
|---|---|---|
| SK00 | [personal-learning](../../personal-learning-suite/src/skills/personal-learning/SKILL.md) | 自然开始、恢复、求助、作品入口和控制；开发命令按需 |
| SK01 | [learning-goals](../../personal-learning-suite/src/skills/learning-goals/SKILL.md) | 目标与判据 |
| SK02 | [learning-materials](../../personal-learning-suite/src/skills/learning-materials/SKILL.md) | 来源、材料与参考 |
| SK03 | [learning-teaching](../../personal-learning-suite/src/skills/learning-teaching/SKILL.md) | Encoding/Post 教学 |
| SK04 | [learning-assessment](../../personal-learning-suite/src/skills/learning-assessment/SKILL.md) | 条件化评价 |
| SK05 | [learning-planning](../../personal-learning-suite/src/skills/learning-planning/SKILL.md) | 需求安排与连续性 |
| SK06 | [learning-strategies](../../personal-learning-suite/src/skills/learning-strategies/SKILL.md) | 按需选择教学方法 |

## 核心规则与按需路径

- 唯一字段与语义维护源：[共享契约](../../personal-learning-suite/contracts/shared-contracts.md)。人工模板不另创正式 schema。
- 首次目标：[目标设计](../../personal-learning-suite/src/skills/learning-goals/references/goal-design.md)。
- 复杂正文、深度或当前展开不清：[目标实例与现有对象的短视图](../../personal-learning-suite/src/skills/learning-goals/references/goal-worked-design.md)，按实际用途推出判据，不自动加最小性／延迟要求。
- 资料进入与核验：[材料工作流](../../personal-learning-suite/src/skills/learning-materials/references/materials-workflow.md)、[领域核验](../../personal-learning-suite/src/skills/learning-materials/references/domain-checks.md)。
- 需要落实框架／例题／图／规格：[材料实例](../../personal-learning-suite/src/skills/learning-materials/references/materials-examples.md)，从实际功能接学习者操作；实例图仅在相应用途下加载。
- 陌生单元／尚无可执行活动：先读 SK03 的 [内容准备](../../personal-learning-suite/src/skills/learning-teaching/references/design-whole.md)，按内容加载 Encoding；首次实例化可参考 [正常教学实例](../../personal-learning-suite/src/skills/learning-teaching/references/teaching-examples.md)，不把例子固定为每次课程。
- 当前教学：[C0](../../personal-learning-suite/src/skills/learning-teaching/references/c0.md)，按需要加载 [Encoding](../../personal-learning-suite/src/skills/learning-teaching/references/encoding.md) 或 [Post-Encoding](../../personal-learning-suite/src/skills/learning-teaching/references/post-encoding.md)。
- 复杂证明/完整代码：[整体设计与核验](../../personal-learning-suite/src/skills/learning-teaching/references/design-whole.md)。
- 评价：[证据规则](../../personal-learning-suite/src/skills/learning-assessment/references/evidence-rules.md)；争议与重要结论加载 [诊断与复核](../../personal-learning-suite/src/skills/learning-assessment/references/diagnosis-review.md)。
- 完整证明／构造／代码／综合论证结论：[整体作品评审](../../personal-learning-suite/src/skills/learning-assessment/references/product-review.md)，沿连续原件查条件与接口；算例和局部题数不替代。
- 计划：[投入与安排](../../personal-learning-suite/src/skills/learning-planning/references/planning.md)、[恢复](../../personal-learning-suite/src/skills/learning-planning/references/recovery.md)。
- 课程／阶段／周取舍或缩时积压：[多尺度计划实例](../../personal-learning-suite/src/skills/learning-planning/references/multi-scale-plan.md)，四种视图共用当前目标、需求和预算；普通问答不预载四层计划。
- 选法：[方法适配](../../personal-learning-suite/src/skills/learning-strategies/references/selection-adaptation.md)，从具体工作发现候选，按需读完整包或未编译原卡；不预载整个策略库。Post 的 [功能与四包入口](../../personal-learning-suite/src/skills/learning-teaching/references/post-encoding.md) 支持恢复、关系、自主选用、条件更新及组合顺序；首次实例化可参考 [方法与 Post 实例](../../personal-learning-suite/src/skills/learning-teaching/references/method-post-examples.md)。
- 维护修复或用户明确有限试用：[验证与收口](../../personal-learning-suite/src/skills/personal-learning/references/verification.md)。内容、实际执行、真实表现与可比成本分别核；真实验证索引引用本目录现有原件，不复制个人内容到通用validation，日常问答不预载这套检查。

规则文件路径及公共文件指纹登记于 framework-manifest.json。指纹用于识别规则修订，不证明学科正确或模型能力。规则变化后重新核对受影响用途，不能据“最新版本”自动撤销旧表现。

实际调试程序时才加载 [材料运行接口](../../personal-learning-suite/src/skills/learning-materials/references/runtime.md)、[评估运行接口](../../personal-learning-suite/src/skills/learning-assessment/references/runtime.md)、[计划运行接口](../../personal-learning-suite/src/skills/learning-planning/references/runtime.md)。它们的 JSON、Grant、SQLite 与事务说明不作为人工开课门槛，真实记录不进入 synthetic 程序。
