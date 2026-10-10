# 本轮审查覆盖与逐文件处理清单

日期：2026-10-04。与 [综合报告](../AI个人学习系统_全套Skill与Agent内容兑现审查及重构判定_2026-10-04.md)共同使用。下表列出当前全部活跃 Agent／Skill 指令文件；目录导航另计，开发程序不是自然语言指令文件。

## 1. 活跃指令：31 份，全部全文读取

由 `rg --files personal-learning-suite/src/agents personal-learning-suite/src/skills` 重新清点：4 个 Agent、7 个 SKILL、20 个 references。原先把 `src/README.md` 与指令混计得到 32；本表已纠正。各分审查者全文读取所负责文件，主审交叉核对核心入口和反证。

文件链接相对本清单；简称 G=目标与评价审查，M=材料与策略审查，T=教学与计划审查，P=主审。结论是该文件对应能力的处理范围，不表示文件中的每一句都需要更改。

| 文件 | 全文审查 | 关联正式依据 | 处理判定 |
|---|---|---|---|
| [AG0-coach.md](../../../personal-learning-suite/src/agents/AG0-coach.md) | T、P | D04—06、D08—10、N00 | 重整当前教学入口、明确未准备活动的准备路径；移出开发历史；保留原答、权限和恢复 |
| [AG1-design-planning.md](../../../personal-learning-suite/src/agents/AG1-design-planning.md) | G、T、P | D02、D04—08、N00 | 补实质备课与短教学交付；移出开发历史；保留目标／计划责任 |
| [AG2-materials.md](../../../personal-learning-suite/src/agents/AG2-materials.md) | M | D03、D09—10、N00 | 保留主体；补当前输入与材料功能交接；整理历史 |
| [AG3-assessment.md](../../../personal-learning-suite/src/agents/AG3-assessment.md) | G | D02、D09—10、N00 | 保留主体；补复杂作品／已有学科核验的采用实例；整理历史 |
| [SK00 SKILL](../../../personal-learning-suite/src/skills/personal-learning/SKILL.md) | P | D00—01、D09、N00 | 重整人工教学与虚构开发两条入口；保留程序边界 |
| [SK00 entry-controls](../../../personal-learning-suite/src/skills/personal-learning/references/entry-controls.md) | P | D00—01、D09—10 | 保留控制和恢复；开发命令按需加载 |
| [SK00 vertical-workflow](../../../personal-learning-suite/src/skills/personal-learning/references/vertical-workflow.md) | P | D00—01、D09 | 保留保存／采用顺序；补用户请求到专业准备的路由 |
| [SK00 network-host](../../../personal-learning-suite/src/skills/personal-learning/references/network-host.md) | P | D09、N00 | 保留宿主真实边界；归入开发／有宿主时的路径 |
| [SK01 SKILL](../../../personal-learning-suite/src/skills/learning-goals/SKILL.md) | G | D02、N00 | 保留；强化到近期教学视图的接口 |
| [SK01 goal-design](../../../personal-learning-suite/src/skills/learning-goals/references/goal-design.md) | G | D02 | 保留目标粒度／前置／证据与输入短路；补复杂内容连贯实例 |
| [SK01 version-rules](../../../personal-learning-suite/src/skills/learning-goals/references/version-rules.md) | G | D00、D02 | 保留；目标正式变更与临时缩时分开 |
| [SK02 SKILL](../../../personal-learning-suite/src/skills/learning-materials/SKILL.md) | M | D03、N00 | 保留；加强陌生单元正向准备入口 |
| [SK02 materials-workflow](../../../personal-learning-suite/src/skills/learning-materials/references/materials-workflow.md) | M | D03 | 补材料形式→功能、当前必要输入；保留六种取舍与完整语义 |
| [SK02 domain-checks](../../../personal-learning-suite/src/skills/learning-materials/references/domain-checks.md) | M、P | D03、D10 | 保留领域与对象核验；由目标、教学和评价按需复用 |
| [SK02 runtime](../../../personal-learning-suite/src/skills/learning-materials/references/runtime.md) | M | D01、B2b 局部接口 | 保留程序边界；日常教学不常驻开发 API |
| [SK03 SKILL](../../../personal-learning-suite/src/skills/learning-teaching/SKILL.md) | T、P | D04—06、N00 | 重编正向教学主干和必要资源路由 |
| [SK03 c0](../../../personal-learning-suite/src/skills/learning-teaching/references/c0.md) | T | D04 | 补正常入口／输入与工作衔接；保留帮助、原答、停止与返回 |
| [SK03 encoding](../../../personal-learning-suite/src/skills/learning-teaching/references/encoding.md) | T | D05、R01—03 | 重点重编内容分析、条件化输入／示范、连贯任务和动态展开 |
| [SK03 post-encoding](../../../personal-learning-suite/src/skills/learning-teaching/references/post-encoding.md) | T | D06、R04—06 | 保留恢复／结构分流等核心；补四份完整资源的触发与内容实例 |
| [SK03 design-whole](../../../personal-learning-suite/src/skills/learning-teaching/references/design-whole.md) | T、P | D04—06 | 补可靠内容到可直接教方案；保留完整产物与核验条件 |
| [SK03 runtime](../../../personal-learning-suite/src/skills/learning-teaching/references/runtime.md) | T | B3b／B4 局部接口 | 保留承载边界；与专业教学规则分层 |
| [SK04 SKILL](../../../personal-learning-suite/src/skills/learning-assessment/SKILL.md) | G | D02、N00 | 保留；补复杂整体评价及领域规则采用入口 |
| [SK04 evidence-rules](../../../personal-learning-suite/src/skills/learning-assessment/references/evidence-rules.md) | G | D02、D10 | 保留证据专业核心；补复杂产物实例与前向验证 |
| [SK04 diagnosis-review](../../../personal-learning-suite/src/skills/learning-assessment/references/diagnosis-review.md) | G | D02、D10 | 保留替代解释、是否值得诊断、停止与纠错 |
| [SK05 SKILL](../../../personal-learning-suite/src/skills/learning-planning/SKILL.md) | T | D08、N00 | 保留；补四层计划和短教学综合视图 |
| [SK05 planning](../../../personal-learning-suite/src/skills/learning-planning/references/planning.md) | T | D08 | 补真实优先级／替代项及多尺度安排；保留成本、需求和标准 |
| [SK05 recovery](../../../personal-learning-suite/src/skills/learning-planning/references/recovery.md) | T | D08—10 | 保留可信断点、缩时和后续条件 |
| [SK06 SKILL](../../../personal-learning-suite/src/skills/learning-strategies/SKILL.md) | M | D07、N00 | 加强实际工作到候选及完整包的导航 |
| [SK06 selection-adaptation](../../../personal-learning-suite/src/skills/learning-strategies/references/selection-adaptation.md) | M、P | D07、D05—06 | 重构具体候选／排除／改道；保留准入、组合、部分借用、返回 |
| [SK06 reuse-change](../../../personal-learning-suite/src/skills/learning-strategies/references/reuse-change.md) | M | D07 | 保留跨次复用、观察限界与实质维护 |
| [SK06 runtime](../../../personal-learning-suite/src/skills/learning-strategies/references/runtime.md) | M | B3c 局部接口 | 保留完整加载和虚构配置边界；不把未编译等同于不可教学 |

## 2. 19 份登记来源的实际覆盖

源路径和优先级来自 `resources/source-registry.json`；本轮没有重新核全部散列或外部论文。以下是审查组联合范围，不代表每人都重复全文阅读。

| 来源 | 本轮范围 | 主要承担者 |
|---|---|---|
| N00 工作网络与实施路线 | 正文全文，重点专业资源转译、正常流程、首期和验收 | P |
| D00 整体概念架构 v1 | 正文全文，当前规范、流程、目标深度和控制 | P |
| D01 Skill 架构 | 正文全文分段核对；补读被输出截断的宿主／工具／用户交互段 | P |
| D02 工作包2／3 | 正文全文，包括近期内容展开和学科判据 | G |
| D03 工作包4 | 正文全文，包括材料功能、复杂参考、跨表征和案例 | M |
| D04 C0 | 正文全文 | T |
| D05 Encoding | 正文全文 | T |
| D06 Post-Encoding | 正文全文，另以完整包复核其源段 | T、M |
| D07 工作包6策略规则 | 正文全文 | M |
| D08 工作包7计划 | 正文全文 | T |
| D09 工作包8协作 | 正文分段阅读全文；核专业交付、正常协作和成本简化 | P |
| D10 工作包9 | 正文联合全文：P 读取1—155、273至末；T 读取155—272 | P、T |
| D11 工作包10 | 正文分段阅读全文；补读比较、修复、验证记录和实施顺序 | P，T定点反查 |
| R01 Encoding研究 | 正文联合全文：M 1—198、223—316；T补199—222、317—539；G另定点反查 | M、T、G |
| R02 60卡Markdown及共同约定 | 全文，包括全部60卡、文首／文尾约束 | M |
| R03 同库JSON | 全60卡非正文字段、顶层约定及46项来源表；所选11卡等完整正文；其余卡专业正文以R02全文审查，JSON载体作一致性检查 | M |
| R04 Post快速矩阵 | 全文 | G、M、T |
| R05 Post深度研究 | 本地正文1—466全文；其他分工定点反查及完整包核对 | T、M、G |
| R06 49项台账 | 本地正文326行、全部49项与审计说明；未重新查外部论文 | M |

R02 与 R03 是同一库的两个载体。不能把重复内容算成两份研究证据，也不声称本轮逐条独立语义复审了 R03 的全部 JSON 正文；其操作内容由 R02 全文承接，JSON 额外元数据已单独检查。

## 3. 其他关联材料

工作包2／3、4、5三方案、7的顶层分析／提示／相关审阅由 G／M／T 按分工读取，具体文件见分报告。没有独立命名的 C0 顶层分析；已有提示、方案和审阅已读。工作包6的正式规则方案是该部分专业依据，不为不存在的同名提示／分析补造文档。

主审补读工作包8、9、10的相关分析与提示；工作包9分析／提示由主审补齐，目标审查者后续补读因调用限制未完成，该失败不计为已读。工作包9明确要求正常经历、可理解当前工作及允许示范，也反对只演练异常，支持本轮补正常备课验收的判定。

相关规格、contracts、实施、前向验证的全文／定点清单分别保存在三个分报告。主审另核 SK00 三份 references、当前人工 MODEL_ENTRY／START_PROMPT、B7 专项规格／实施与收口，以及 source registry 的来源／优先级和路径。

实际只读执行：64项策略索引；四 Post 完整 `StrategyCatalog.load`；未编译 R07 的回源返回。没有创建真实学习事件，没有执行新教学试验，没有重跑整个 Python 测试集。

## 4. 边界

本轮“全部”指当前31份 Agent／Skill指令，及其登记专业研究／正式设计的内容对照。没有逐行审计所有 Python、所有历史临时备份、所有回归输出、机器上所有外部 Skill 或49篇外部论文。WM 聊天事实承接已完成的12轮读取与专门报告，没有把其原答复制进通用资源。

全套指令已读和当前判断成立，不等于真实教学有效、各种学科可靠评分、宿主权限保证或低等待已经验证。前向与真实效能缺口已在综合报告中明确列为后续验收。
