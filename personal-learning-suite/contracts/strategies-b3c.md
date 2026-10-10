# B3c 策略资源与选法切片 pl-strategies/0.1.0

日期：2026-10-03；共用协议沿用 `pl-contracts/0.1.0`，个人保存沿用 `pl-store/0.1.0`，当前 context 输入适配为 `pl-strategies-input/0.2.0`。这是 [共享契约](shared-contracts.md) 对 `MethodConfig` 的局部嵌套适配；与 C0／评估的配置、材料用途和阶段连接见 [B3 联合接口约定](b3-interop.md)。不另建顶层学习对象或第二份共享必填字段表。

## 能力与范围

[learning-strategies](../src/skills/learning-strategies/SKILL.md) 指导 AG1 完成选法、组合、适配、替换和跨次维护。确定性 [learning_strategies.py](../src/runtime/learning_strategies.py) 只检查明确虚构工作区的来源约束、声明完整性、引用和当前范围相容性；它不生成学科题目，不核验内容正确性，不识别所有语义／视觉泄露，不评分、调度或验证效果。`compatible` 不代表可靠专业结论或学习已发生。

通用资源保存在 `resources/strategies`，不包含个人目标、原答或使用分析；个人配置保存在 B1 学习工作区，引用通用资源修订。CLI 的受控 `entry_actor` 是测试配置，不认证 AG1 身份；本批未绑定常驻 Agent、真实课程、教学展示或已安装 Skill。读 Skill 或返回结构成功不提供新授权。

## 资源加载

`strategy-index.json`为导航，当前60个Encoding原ID全部有完整包，另有四个Post包：`post/retrieve-relation`、`post/select-method`、`post/conditional-update`、`post/retrieve-generate-order`。`intended_work`帮助从认知工作发现候选，`compiled`及`bundle_path`说明正文可读；读取、适配、专业采用和实际教学分别成立。未来新增未编译项仍保留原文位置，不解释为方法不存在。完整包保留原始两载体、前后共用约束、认知目的／操作／风险／验收及全部原证据定位；不新增经过实验验证的主张。

已编译 Encoding 包携带 R03 完整 `content_markdown`、R02 同卡正文及文首／文尾共用约束，保留原 ID、`source_version=2.0`、`template_status`、`evidence_ids` 和来源位置。R02／R03 是同一库的载体，不计为独立研究。R09 的 `evidence_ids=[]` 和设计综合主张不得被补写为实证支持或自动禁用。

Post 资源键注明套件新增，引用 D06 的活动语义、R04 导航、R05 对应正文和必要 R06 条目。矩阵为非互斥导航，文献 E 编号只作证据定位，D06 的 P 编号不作方法 ID；不能编译统一“检索在先”、固定成功率、复习间隔或生物机制状态。

每个完整包的 `conditions` 用 `key/required_for/scope/explanation` 保留新增整理的检查点。`scope=requirement` 为必要条件，`scope=exclusion` 为排除条件；`required_for` 按 teaching／independent 区分。结构化标签是本套件的整理，不能误称原 JSON 已有机器准入规则。索引、正文存在和文件指纹不证明研究或本题正确。

## 当前工作 context

`inspect` 与 `submit` 使用以下局部视图，不替换共享 `WorkOrder`。引用均为精确 ObjectRef，事实沿共享 Fact 语义。

| 字段 | 表示与限制 |
|---|---|
| synthetic_only | 固定 true，不能携真实记录进入开发助手 |
| intended_work | 非空具体教学工作，与配置一致，不用卡名代替 |
| goal_refs / activity_ref / material_refs | 目标、活动和当前用途材料的确切对象修订；引用须可读、当前且未受相关控制限制 |
| material_context | 必填完整 B2b 上下文：activity_ref／goal_refs／intended_use／required_modalities／conditions／purpose；与已核 MaterialUse binding 及本次对象精确匹配，并重新检查用途。不能只凭 supported／checked_revision 放行 |
| purpose | teaching 或 independent；独立指关键操作由学习者完成，可使用目标允许资源 |
| conditions / allowed_resources | 当前声明条件与允许资源的字符串列表；不能把未记录解释为空 |
| budget_ref | 当前共用预算 ObjectRef，不复制或扩大额度 |
| requires_time_condition | 是否由本目标要求时间条件，未要求时不造延迟债务 |
| selection_needed | 是否存在当前选法／适配／维护需要，false 时不强制遍历库 |
| existing_activity_reliable | 用于可靠旧活动短路的 Fact；需 known true 且无选择需要，返回无新配置 |

局部视图不增加教学展示权。方法 purpose 说明本次保留的学习者工作，material_context.purpose 说明材料分区用途，二者独立；teaching 方法可以使用已核的独立题面，不能据方法用途扩大材料使用。完整 material_context 纳入配置 review 绑定，缺失不由运行器猜造。运行助手只能检查声明与已存对象；真实帮助、接触、时间及父产物仍依据 C0 原记录。未知不补造为无暴露、无帮助或零成本。

独立用途的时间范围绑定当前活动的 `criterion_refs`，不只信任调用方布尔声明。沿 B3a 的局部表示，GoalSpec.time_requirements 可为 known.value={requirement_ids:[...],minimum_delay_seconds:...,require_no_contact:...}；本助手仅核 `requirement_ids` 与当前 `requirements/<id>` 的相交范围。未知或无法定位时保持受限，不按全文猜测；not_required／不相交要求不能被声明成当前必需延迟。实际延迟与无接触资格由 SK04 核查，本助手不据 time_condition=true 认证保持。teaching 用途可继续当前建构，不为目标的未来时间条件阻断输入或生成额外活动。GoalSpec.allowed_resources 可沿既有表示为列表或 known.value 列表，未知不能扩大允许资源。

## MethodConfig 嵌套表示

顶层必备字段及 AG1 归属以共享契约为唯一源；本节仅规定本切片读取的嵌套结构。

| 共享字段或局部扩展 | B3c 表示 |
|---|---|
| source_refs | 沿用 source_id／declared_revision／locator／identity_kind，恰好保留所选完整包来源的并集，不额外夹入未登记研究来源；resource_key 可定位借用包。card、document_section、literature_entry 表示定位类型，不能当权威或效果等级 |
| resource_revision | 当前编译版本 `pl-strategies/0.1.0`；不代替原卡库版本 |
| selected_parts | 条目为 resource_key／resource_revision／borrowed_parts／omitted_parts／non_equivalence；两部分用字符串列表，只借用部分时说明未做及不等效处 |
| prerequisites / exclusions | `[{condition, check:Fact}]`；已核必要条件为 known true，已核排除未触发为 known false；unknown、不适用与未执行不能伪装成布尔通过 |
| resource_checks（扩展） | `{resource_key:{condition_key:Fact}}`；按每个完整包 conditions 的 key 覆盖核对当前用途必要点，known 布尔含义同上 |
| required_learner_operations | 非空字符串列表，说明实际保留的关键工作，不记录发生事实 |
| help_and_feedback_constraints | feedback、exposure、contact_history、time_condition 为 Fact；另有 allowed_resources、provided_operations 字符串列表。必要反馈要有可兑现依据，独立用途不得声明关键操作已由输入代做；时间仅在目标要求时必需 |
| adjustable_parts | 可以调整的对象、表示、材料或帮助范围；不因此免核实质内容／操作改变 |
| combination_and_non_equivalence | rationale、interference_check:Fact、single_performance:true、alternatives；说明组合理由、相互泄露与实际替代的保留／损失。多个来源指同一实际工作仍只有一次表现 |
| cost | preparation／execution／feedback／verification／closure 和 budget_fit 均为 Fact；阶段成本可未知，估计保留依据，当前可行性不能以未知默认通过 |
| interruptibility | Fact；known.value 可保留可暂停位置与恢复代价，unknown 保留未核原因，不制造通用分钟数；具体父产物仍由活动维护 |
| stop_or_return_conditions | 非空停止／回退／返回说明，引用活动范围，不无限追加任务 |
| evidence_limits | resource_limits 按 resource_key 原样携带完整包 evidence_limits；config_limits 为非空当前限制说明，不能用局部表述抹掉原证据边界 |
| original_claim_status | 按 resource_key 原样携带完整包 original_claim_status；H／设计综合和 R09 空引用保持原性质 |
| local_adaptations | 当前改动及理由，未改可确知为空；不是已完成教学记录 |
| review_status | `{status:'reviewed',reviewer:'AG1',binding:{...}}`；binding 精确复制 context 的 synthetic_only、intended_work、goal_refs、activity_ref、material_refs、material_context、purpose、conditions、allowed_resources、budget_ref、requires_time_condition。selection_needed 和 existing_activity_reliable 只控制路由，不进入此绑定。review 只表示配置声明的审查，不表示内容、方法效果或采用 |
| reuse_limits | 非空适用／失配／重核条件；新版不无条件覆盖旧结果 |
| previous_config | null 或确切旧配置 ObjectRef；保留旧版及停止／变化原因 |
| adoption（扩展） | 显式专业采用，如 `{status:'adopted',by:'AG1',scope:'当前活动的明确配置范围',basis_refs:[ObjectRef],limitations:['当前限制'],time:{status:'not_executed',reason:'人工演示未发生真实采用'}}`；时间未记录则用带原因的 unknown Fact，不能补造真实采用时刻。范围若用结构字段须与本次 context 一致；缺范围／限制／时间不能作为已采用配置执行。inspect 不自动采用，submit 沿 B1 授权、采用和当前版本门禁 |

source_refs、evidence_limits 和 original_claim_status 不能通过删除条目或改用文献号绕过完整约束。review_status.binding 中用途、目标、活动、材料、条件、资源、预算或时间要求变化时，须重新声明并检查；旧 review 不能自动授权新用途。

本助手采用有限保守切片：未编译或必要条件未确认时返回受限候选及缺项，而非提交正式可用配置。教学不依赖该未知的可靠范围可由 SK03 继续；程序受限不等于通用方法不可用。

## 命令、保存与变更

`index` 只返导航；`load` 返回选中包的完整资源或未编译回源结果；`inspect` 检查虚构当前工作与候选，无写入、无采用。已有可靠活动无需重选时可以 config=null 返回复用，不生成空壳 MethodConfig。

`reuse` 接收 config_ref／context，读取已保存且显式采用的配置，核它仍为当前修订，再复验当前声明。成功返回 reusable、adopted=true、teaching_started=false；不重新创建配置或记录活动发生。目标、材料、条件、预算或限制变化可使原配置受限；旧修订不能伪装当前依据，previous_config 的精确历史定位仍保留。旧配置没有 material_context review 绑定时需 AG1 重核，历史记录保持原样，不能把输入版本变化自动视为重新采用。

B3b 可通过本次请求 method_config_refs＋strategy_context 显式连接该配置，复验后记录事件实际使用的引用；不要求把配置回写 ActivitySpec。B3a 回查历史事件时保留当时配置修订，不因新版发布改写实际帮助或原答。当前执行资格与历史条件分开，删除和用途门继续优先。

`submit` 的请求沿用 expected_state_revision／operation_id／changes／authorization_refs／adoption_refs 和必要 context，经原 `LearningStore.commit` 保存。AG1 授权应已存在，不能同批新造权限；现代 validity 必须 known.value.active=true，未知／false Fact 不因非空通过，旧 B0 prose 夹具只保留明确开启的读取兼容。助手每次只提交一个 MethodConfig，不夹带新原件或 WorkResult。WorkResult 的语义交付继续沿共享契约，可由既有 B1 入口另行处理。显式采用不替代授权，review_status 不替代采用。控制、依赖修订、对象范围、CAS 和幂等都继续生效；同一次逻辑操作重试不新建配置、样本或需求，旧候选不覆写新修订。

`change` 可给 changed_refs（已存 MethodConfig 精确 ObjectRef）、resource_keys（通用资源键）或 resource_changes（`[{source_id,previous_revision?}]`）。资源变化先按已记录 selected_parts／source_refs 定位个人配置，再沿其 ObjectRef 查直接／传递依赖；不将 D／R／文献来源伪装为个人对象，不自动扫描全文寻找语义使用。无匹配也保持 unknown dependencies，不能声称资源没有影响。输出待处理范围及责任；字段匹配不是完整语义影响证明。显式限制选项才调用原 B1 用途限制 API。历史事件仍引用当时配置，原答、帮助、判断、目标和计划均不自动改写，也不自动补测或解除限制。

CLI 从套件目录执行 `python src/runtime/learning_strategies.py <command>`。index 可加 `--work` 做文本导航；load 使用 `--resource-key`。inspect／reuse／submit／change 要求 `--workspace` 与 `--request`（UTF-8 JSON）；inspect 请求为 config／context，config 可在可靠活动短路时为 null，reuse 请求为 config_ref／context。change 至少有 changed_refs／resource_keys／resource_changes 之一，`--restrict` 时还需 expected_state_revision／operation_id／intended_uses／reason。成功导航／加载为 ok，未编译为 needs_source_review，检查为 compatible／limited／direct_reuse，已采用配置复验为 reusable；控制或资源缺失可为 blocked，非法请求 rejected，保存返回沿 B1 committed／conflict／rejected／not_saved。

原来源或运行包指纹与 manifest 不符时，加载返回 resource_integrity_unavailable，停止使用该编译发布切片并回源复核；程序不会自动生成新指纹或认证新正文。这个保守门禁可能限制整份 manifest 的加载，不是按内容建立的完整影响分析。

删除、暂停和限制优先于读取或提交；迟到载荷不得恢复被删原答／配置。B1 删除覆盖其受控数据库和管理副本，不覆盖 CLI request 文件、stdout、外部备份或已加载上下文。退出个人配置不删除通用卡库；通用资源修改为独立开发维护改动，不由使用反馈自动更新。

## 设计要求与本批选择

D07、D04—D06、D08 和路线规定职责、来源完整、实际帮助、条件化选择、可靠直接教学路径及保存／控制语义。本批新增的是资源键、conditions／resource_checks、有限 compiled 子集、上述嵌套检查和六个 CLI 入口；这些实现选择可随后续实际用途调整，不解释为设计已经规定唯一 schema、最佳算法或固定教学流程。
