# 共用契约 pl-contracts/0.1.0

日期：2026-10-02。范围：B0 建立的共用规范基线。B1 承载接口见 [保存与入口接口](runtime-b1.md)；真实宿主身份绑定与运行保障尚待后续验证。

依据：N00 第四至八、十至十三节；D00 第一、三、五、六、八、九节；D01 第六、七至十一节；D02—D08 的专项接口；D09 第二至九节。编号和文件指纹见 [来源登记](../resources/source-registry.json)。

本文是唯一共用语义及字段维护源。下方 JSON 是本文内的静态字段约束，检查脚本直接读取它，不另维护手写 schema。专业任务单引用本文。未来发布副本必须由此生成并检查版本一致。0.1.0 只冻结已明确的接口；B1 的存储布局、原子发布、身份映射、删除报告和错误返回需另作实现设计。

## 1. 共同表示

对象具有 `type/id/revision/owner/schema_version/basis_refs`。`revision` 是正整数内容修订；`schema_version` 固定为 `pl-contracts/0.1.0`，不代替目标或判据内容修订。稳定 ID 在同一对象修订间不变，跨对象不复用；引用使用 `{id, revision, locator?}`，历史内容引用具体修订，不偷偷跳到最新。

来源、题面、原答和父产物须有定位。`ArtifactRef` 是 `{path, locator, revision, origin}`；`origin` 可为 `learner_original`、`teacher_reference`、`generated_material` 或 `synthetic_fixture`。个人原件的路径由真实学习工作区解析，不能指向本套件；虚构原件只在 fixtures 中。AI 润色稿另存派生位置，不能替换原答。

需要区分未知的事实用 `Fact = {status, value?, reason?}`。状态为 `known/unknown/not_required/not_applicable/not_executed/deleted`；known 必须有 value，其他状态须有原因且不携带猜造 value。空列表只有在确知为空时使用；缺字段、null、没有记录都不能解释为无帮助、无接触、零成本或已通过。`deleted` 仅表示范围失效，不能携带正文、摘要、内容指纹或可重建信息；若删除包含关联索引，不再保留该标记。

`SourceRef` 在 SourceFragment 中为 `{source_id, declared_revision, locator, identity_kind}`。设计来源用 D/R/N 编号；真实课程来源独立登记；虚构来源使用 `FIX-*`，不得进入通用资源的 D/R/N 台账。文件指纹仅检测非个人设计资源变化，不证明可靠。

`basis_refs` 引用实际依赖；无依赖的原始来源或用户授权可为空，说明出处仍在其专有字段。首期从对象引用扫描生成反向关系，`DependencyEdge` 是可生成视图，不另维护权威图数据库。

## 2. 对象与责任

| 对象 | 专有必备字段与语义 | 主责与边界 |
|---|---|---|
| LearningInstance | course、purpose、scope、user_constraints、actor_bindings、record_root、record_control_scope；事实可未知 | AG1 组织，专业方补齐；课程和个人基础不得从设计案例推断 |
| GoalSpec | requirements、requirement_source_refs、content_basis_refs、prerequisites、allowed_resources、context_conditions、time_requirements、evidence_requirements、version_compatibility | AG1；每个 requirement 有稳定 requirement_id、关键操作、产物、criterion 与 criterion_revision、要求性质；用户用途/课程要求/系统建议/待澄清分开标明；前置和判据也关联两类来源 |
| SourceFragment | source_ref、read_scope、claims、verification、unread_parts | AG2；文字/公式/图表分别记录读清范围、条件、核验方式和限制；能打开不等于读清或核验 |
| MaterialUse | goal_refs、fragment_refs、intended_use、visible_input、backup_help、teacher_reference、verification、leakage_risk、limitations | AG2 维护用途；实际展示由 AG0 写事件。核验分内容正确性和当前用途资格；prepared 不等于 displayed |
| ActivitySpec | goal_refs、criterion_refs、prompt、learner_operations、material_refs、reference_refs、task_qualification、branches、authority_refs、parent_task、budget_ref、stop_conditions、return_conditions | AG1 关键设计；AG0 可在授权内适配。任务资格单列目标操作调用/未代做/前置负担/参考可评分/证据条件；父产物保留规范位置、卡点、转入依据及替代解释、局部够用条件和返回连接；简单任务显式不适用 |
| PerformanceEvent | activity_ref、goal_refs、original_response、revisions、contributors、timeline、actual_resources、contact_history、occurred_at、independent_sample_id、method_config_refs | AG0 记录发生事实。修订仍在同一事件；时间线含 ExposureEvent 和原答/帮助/反馈/修订顺序，实际帮助及替代操作；同一事件跨要求引用不新增样本 |
| Judgment | goal_ref、requirement_id、criterion_revision、event_refs、conditions、support、eligibility、intended_uses、rationale、unsupported_scope、counterevidence、authorization_ref、decision_type、adoption | AG3；AG0 仅获授权常规判断。按要求及条件分双轴，不能只存 mastered；重要跳过/整体评审/争议/新解/结论扩展须重要复核 |
| DiagnosticNote | goal_refs、decision_question、observations、explanation、alternatives、counterevidence、next_observation、decision_branches、budget_ref、authorization_ref、decision_type、stop_condition、stop_reason、reopen_condition | AG3 或 AG0 的有限授权；授权主体与 limited_diagnosis 范围须可核查。指明哪些观察会改变哪项安排。原因标签不是稳定心理事实；预算/分支可明确引用 ActivitySpec |
| LearningNeed | goal_ref、requirement_ids、needed_work、necessity、non_action_consequence、conditions、parent_task、judgment_refs、requester、assignee、acceptance、disposition、uncovered_impact、next_trigger | AG0/AG3 提出、AG1 维护去向；连续同类错误更新同一需求。未接责由 requester 跟进；接责不等于安排 |
| PlanCommitment | goal_refs、need_refs、executable_scope、adopted_basis_refs、budget_ref、authorization_refs、allowed_adjustments、unselected_consequences、checkpoint_ref、next_trigger、status | AG1；AG0 授权内缩时/滚动。唯一有效承诺按范围维护，预算变化不改 GoalSpec；排期不算发生或达成 |
| MethodConfig | intended_work、source_refs、resource_revision、selected_parts、prerequisites、exclusions、required_learner_operations、help_and_feedback_constraints、adjustable_parts、combination_and_non_equivalence、cost、interruptibility、stop_or_return_conditions、evidence_limits、original_claim_status、local_adaptations、review_status、reuse_limits、previous_config | AG1/SK06；原 ID、版本和借用部分保留，旧配置/停用理由可定位；研究文献号不是操作卡号。无合格配置仍可直接可靠教学 |
| WorkOrder | operation_id、requester、assignee、decision_needed、decision_type、scope、output_contract、goal_and_criteria_refs、material_refs、event_refs、current_restrictions、basis_revisions、execution_epoch、authority_scope、authorization_refs、shared_budget_ref、stop_condition、return_owner、next_trigger、acceptance | requester 与 assignee 各有阶段责任；接收者须有与 decision_type 相容的显式授权，尚未落实则任务保持候选未就绪，不能引用发起方授权冒充接收方权限；模式不赋权；最小上下文引用，预算不复制 |
| WorkResult | work_order_ref、handled_scope、unhandled_scope、result_refs、limitations、adoption_needed、next_owner、next_trigger、compatibility、adoption | 专业返回与采用责任分开；合法事实/候选决定分开，调用成功不等于采用 |
| AuthorizationGrant | issuer、grantee、decision_types、object_scope、criterion_refs、permitted_conclusions、escalation_signals、budget_ref、delegable、validity、binding_status | 用户权限及各专业责任的真实委派；AG3 可授常规评分，重要复核不因模式自报取得；子授权不得扩大父授权 |
| BudgetEnvelope | user_active_time、blocked_wait、system_effort、fees、allocation_scope、authorization_ref、accounting_notes | AG1；值含观测/估计/未知及来源。阶段/周/会话共用额度引用，细分耗时不能重复相加 |
| ControlState | state_revision、restrictions、execution、record_policy、pending_controls | AG0 组织用户控制，专业方管用途恢复；execution 含 activity_ref/current_executor/execution_epoch/status；新提示与正式提交前读取 |
| UseRestriction | scope_refs、intended_uses、reason、issued_by、status、restoration_conditions、restoration_refs | 任一发现者先限制；相应专业方依据恢复。不能因版本更新自动解除 |
| CorrectionCase | changed_refs、reason、affected_refs、unknown_dependencies、restriction_refs、material_recovery、judgment_recovery、teaching_recovery、planning_recovery、next_owner、next_trigger | 四恢复面分别记录；原答够用直接重评，实际教学修复尚未发生不能报完成 |
| SessionCheckpoint | activity_ref、parent_artifact、last_trusted_event_ref、help_history_refs、next_connection、stop_reason、pending_owners、budget_ref、control_ref、unrecorded_actions | AG0 事实断点；可内嵌活动/承诺；无摘要从最后可信事件恢复，未记录动作保持未知 |
| ChangeNotice | changed_refs、reason、immediate_restriction_refs、direct_dependencies、unchecked_scope、restoration_conditions、return_owner | 发现者到相关专业方；同时沿内容链和要求链追溯，不先判用户错误 |
| DependencyEdge | from_ref、to_ref、relation、scope、provenance | 从实际引用生成；未知依赖不默认为不存在；删除覆盖此视图 |
| ValidationDecision | validation_layer、case_id、host、versions、executor、checker、raw_output_ref、status、limitations、cost、decision、replay_of | 开发核查/试用组织；V1—V4 分开，静态检查不算软件行为/学习效果/协作增益；个人内容同样可删除 |

SourceFragment 的统一运行表示（2026-10-04 来源接口修复）：`read_scope` 用 `text/formula/figure` 三个独立 Fact；`claims` 保留已说明的主张列表，尚未解释时可保持 unknown Fact；`unread_parts` 为 Fact。`verification.content` 分别记录 `status=supported/partial/pending/error`、`checked_revision`、`scope`、`conditions`、`unchecked_scope`；支持声明再有 `reviewer=AG2`、`method=source_comparison/derivation/test/expert_review`、可定位的 `anchor_refs`。这些是来源读取与核验声明，不是 MaterialUse 的当前用途资格，也不提供程序内容真伪保证。

统一来源进入目标检查时，`verification.content.required_modalities` 是 AG2 对**当前已声明核验范围**作出的非空 `text/formula/figure` 列表；该范围需与相关目标用途相容，由专业责任方确认。检查器要求列出的模态确为 known、有非空范围说明或定位，布尔“已读”标记不能代替范围；核验支持本对象修订且有方法、条件和锚点。未提供这个范围、必要模态 unknown 或核验 pending／旧修订，只限制关联要求，不猜测、不补默认模态。未被当前范围要求的模态可继续 unknown；目标检查通过不能让它们变为已读。原件锚点在受控保存／材料阶段还须可定位读取，元数据完整不证明锚点内容正确。

B2a 原单 Fact `read_scope` 和 `verification.value.recorded_status=supported_for_fixture` 仅作为已有虚构目标输入的兼容载体保留，不自动转换成三模态事实。它可继续供有限目标预览；进入材料检查前必须由 AG2 显式补齐实际模态与统一核验表示，必要时提交新来源修订并重核关联引用。材料阶段按 `MaterialUse.context.required_modalities` 独立检查当前用途，不能用来源的旧范围填补新用途必要模态。已有统一来源缺 `required_modalities` 仍可保存真实已知的读取事实或进行材料核验；用作目标可靠依据时保持 partial。此细化不改下方 B0 静态必备字段表或历史夹具。

内嵌 ExposureEvent 的字段为 `kind/sequence/visibility/content/target_operations/substituted_operations/time`。visibility 区分 `planned/requested/displayed/backend_reference/unknown`；实际题目标题和安排解释若泄露方法也记 displayed；宿主未确认显示时 unknown。初答、反馈和修订按 sequence 排列，时间未知仍保留顺序。`contact_history` 保存按操作定位的初学、最近相关练习/反馈、再接触；严格无接触只在目标确实要求时检查。

`ParentTask` 在 ActivitySpec.parent_task 为 known 时，其 value 必备 `parent_activity_ref/parent_artifact/blocker/entry_basis_refs/alternative_explanations/local_sufficiency/return_connection/budget_ref`。parent_artifact 是规范 ArtifactRef，不能只写父任务标题；return_connection 说明怎样回到同一未完成产物。LearningNeed 可引用活动的 parent_task 定位而不复制；SessionCheckpoint 引用同一父产物。修复够用不是整体通过，模块切换也不增加样本或第二条同目标复习债务。

ObjectRef 不允许只有 id 没有 revision；对象引用的 _ref/_refs 字段均须可定位具体修订，字段明确接受 Fact 的未知/不适用情况除外；SourceRef 按来源声明修订与 locator 定位。静态夹具中的原答必须有非空 ArtifactRef，时间线须有初答，帮助/修订不能以空列表隐藏。授权除主体和决定类型外还须覆盖对象与判据范围；空 scope 不是全域权限。

## 3. 状态、授权与采用

Judgment.support：`unknown/supported/observed_not_met/mixed_or_conflicting`。Judgment.eligibility：`usable/pending_review/withdrawn`。二者独立；参考疑误可保留正面历史支持而限制用途。GoalSpec.time_requirements 只有确实要求才产生缺项；否则 not_required。同原答同条件冲突回原答和判据，不投票、平均或最后到达优先。

阶段分开保存：提出 → 接责 → 专业采用 → 计划实质处置/生效。同人可在同条记录完成，不强制会签。`acceptance.status` 为 `proposed/accepted/partially_accepted/declined`；须有范围、责任和触发。`adoption.status` 为 `candidate/adopted/partially_adopted/recheck/rejected`；有采用者、依据、范围、限制和时间状态，candidate 不成为当前依据。`LearningNeed.disposition.status` 为 `pending/scheduled/partially_scheduled/merged/deferred/no_further_investment/closed/returned`；非 pending 要求理由、未覆盖影响和下一触发；scheduled/partially_scheduled 须有有效承诺引用，merged 须有原需求要求映射。退出投入可伴随目标未完成。

| 专业决定 | 最终责任 | AG0 可获授权范围 |
|---|---|---|
| 目标/前置/判据/版本 | AG1 + 用户的正式用途/范围选择 | 读取与澄清，不降低正式标准 |
| 材料正确性/用途/内容更正 | AG2 | 已核验材料的可靠等价安排；实质新内容升级 |
| 关键教学设计/方法配置维护 | AG1 | 措辞、许可帮助、有限局部适配，关键操作改变升级 |
| 常规评分/条件化判断/有限诊断 | AG3 可委派 | 指定判据、活动、结论范围和升级信号 |
| 重要复核/非标准解/冲突/删除影响 | AG3 | 保存原答和限制用途，不能自行改判 |
| 需求去向/跨目标取舍/有效承诺 | AG1 + 用户资源取舍 | 授权内收束、缩时和滚动，不能扩大预算 |
| 暂停/记录控制/教学展示 | 用户控制；当前 AG0 执行入口 | 立即限制，并按实际可控范围报告 |

binding_status 为 `unbound/verified_for_fixture/host_verified`。verified_for_fixture 仅供虚构静态检查，不能用于真实执行。角色名、技能模式、字段签名不认证提交者；真实权限必须来自宿主工具边界和可核查绑定。当前共用文件系统下开发子代理不是已部署 AG0—AG3。

结果采用次序：① 在读取/持久化候选前查删除、暂停、停用；② 查真实身份、职责、授权范围和委派上限；③ 查目标、判据、材料用途、任务、实际帮助/接触、预算和依赖修订的兼容；④ 分离可保留新事实和失效旧决定；⑤ 相应专业方采用/部分采用/重核/拒绝；⑥ 仅改变承诺、依据或可执行范围时同步计划。普通原答追加及授权反馈不等计划批准。

`operation_id` 以一次逻辑提交为单位，重试不新增事件、样本或需求；并非每个对象各造一个新操作。B1 提交请求携带 `expected_state_revision/operation_id/authorization_refs/changes/adoption_refs`，返回 `committed/conflict/rejected/not_saved` 及实际影响；开发态 `entry_actor` 是受控测试配置，真实 actor_binding 未实现，不能当鉴权。

## 4. 交付包与调用

| 包 | 发送 → 接收 | 共用对象和接收结果 |
|---|---|---|
| P-Goal | AG1 → AG2/AG3/AG0 | GoalSpec + 两类来源；回复内容/评价可行范围和必要缺项 |
| P-Material | AG2 → AG1/AG0/AG3 | SourceFragment + MaterialUse；回复用途匹配、泄露影响和实际采用范围 |
| P-Activity | AG1 → AG0 | ActivitySpec + GoalSpec/MaterialUse/MethodConfig/PlanCommitment 引用；接受可执行范围或返回必要缺项 |
| P-Performance | AG0 → AG3 或授权本地 | PerformanceEvent + 原答/帮助/判据/参考；Judgment/有限诊断/必要补证或不追加检查 |
| P-Need | AG0/AG3 → AG1 | 同一 LearningNeed + 依据/父任务/条件/代价；实质去向、影响和触发 |
| P-Change | 任一发现者 → 相关责任 | ChangeNotice/UseRestriction/CorrectionCase；四面分别处理及尚受限范围 |

Skill 请求以 WorkOrder 或同字段的本地视图表达；Skill 返回 WorkResult 或同字段视图。无需启动另一实例，也无需复制全部个人记录。七 Skill 读取共同控制规则，用户直接调用专业 Skill 且无课程/执行授权时只给候选，不暗建会话、记录或承诺。

## 5. 暂停、删除、接管与恢复

只有一个当前用户教学入口。后台默认不展示；接管核对父产物、帮助、版本、预算和限制，execution_epoch 增加且旧范围展示权终止。epoch 只是记录；宿主无法拦截旧输出时采用单入口串行，先确认旧执行结束。不能确认唯一入口就停同活动新题目和提示。旧工作可保留的后台核验范围另授权。

删除先限制、再清可控原件/历史/摘要/派生件/临时/候选/运行个人摘录/验证/已管理导出，并停止受影响后台工作与回传。先检查再读取/落盘迟到载荷，禁止已删内容复活。失去依据后 AG3 按剩余合法证据保留、收窄或撤销用途；不自动补测。磁盘清理不代表上下文消失，必要时结束受影响任务，用仅剩合法材料的新上下文；外部历史和备份只能报告不可控范围。普通回滚不得恢复被删内容。

纠错沿内容传播和要求传播两条链，分别完成材料用途、历史判断、实际误导、计划需求恢复。未知依赖保持相关用途受限。不等待完整新版计划才限制。原答足够直接重评；不够时只提会改变决定的必要补证。

恢复先查控制/有效承诺/目标判据/有效判断/材料用途，再查父产物/原答/帮助/断点。本次重新核对投入；没有摘要只用最后可信事实，不全章重测。预算结束、无进展、用户暂停和证据充分分别记录；停止不能记成达成。

## 6. 静态约束单一源

以下 JSON 是 B0 检查使用的最小字段表；业务语义由上文界定。它不是完整 JSON Schema，不覆盖全部嵌套字段类型，也不提供存储/安全/专业正确性保证。未来扩展时直接更新本文，再重跑夹具。

<!-- b0-contract-definition -->
```json
{
  "protocol_version": "pl-contracts/0.1.0",
  "base_required": ["type", "id", "revision", "owner", "schema_version", "basis_refs"],
  "fact_statuses": ["known", "unknown", "not_required", "not_applicable", "not_executed", "deleted"],
  "support_values": ["unknown", "supported", "observed_not_met", "mixed_or_conflicting"],
  "eligibility_values": ["usable", "pending_review", "withdrawn"],
  "objects": {
    "LearningInstance": {"owners": ["AG1"], "required": ["course", "purpose", "scope", "user_constraints", "actor_bindings", "record_root", "record_control_scope"]},
    "GoalSpec": {"owners": ["AG1"], "required": ["requirements", "requirement_source_refs", "content_basis_refs", "prerequisites", "allowed_resources", "context_conditions", "time_requirements", "evidence_requirements", "version_compatibility"]},
    "SourceFragment": {"owners": ["AG2"], "required": ["source_ref", "read_scope", "claims", "verification", "unread_parts"]},
    "MaterialUse": {"owners": ["AG2"], "required": ["goal_refs", "fragment_refs", "intended_use", "visible_input", "backup_help", "teacher_reference", "verification", "leakage_risk", "limitations"]},
    "ActivitySpec": {"owners": ["AG1", "AG0"], "required": ["goal_refs", "criterion_refs", "prompt", "learner_operations", "material_refs", "reference_refs", "task_qualification", "branches", "authority_refs", "parent_task", "budget_ref", "stop_conditions", "return_conditions"]},
    "PerformanceEvent": {"owners": ["AG0"], "required": ["activity_ref", "goal_refs", "original_response", "revisions", "contributors", "timeline", "actual_resources", "contact_history", "occurred_at", "independent_sample_id", "method_config_refs"]},
    "Judgment": {"owners": ["AG3", "AG0"], "required": ["goal_ref", "requirement_id", "criterion_revision", "event_refs", "conditions", "support", "eligibility", "intended_uses", "rationale", "unsupported_scope", "counterevidence", "authorization_ref", "decision_type", "adoption"]},
    "DiagnosticNote": {"owners": ["AG3", "AG0"], "required": ["goal_refs", "decision_question", "observations", "explanation", "alternatives", "counterevidence", "next_observation", "decision_branches", "budget_ref", "authorization_ref", "decision_type", "stop_condition", "stop_reason", "reopen_condition"]},
    "LearningNeed": {"owners": ["AG1", "AG0", "AG3"], "required": ["goal_ref", "requirement_ids", "needed_work", "necessity", "non_action_consequence", "conditions", "parent_task", "judgment_refs", "requester", "assignee", "acceptance", "disposition", "uncovered_impact", "next_trigger"]},
    "PlanCommitment": {"owners": ["AG1", "AG0"], "required": ["goal_refs", "need_refs", "executable_scope", "adopted_basis_refs", "budget_ref", "authorization_refs", "allowed_adjustments", "unselected_consequences", "checkpoint_ref", "next_trigger", "status"]},
    "MethodConfig": {"owners": ["AG1"], "required": ["intended_work", "source_refs", "resource_revision", "selected_parts", "prerequisites", "exclusions", "required_learner_operations", "help_and_feedback_constraints", "adjustable_parts", "combination_and_non_equivalence", "cost", "interruptibility", "stop_or_return_conditions", "evidence_limits", "original_claim_status", "local_adaptations", "review_status", "reuse_limits", "previous_config"]},
    "WorkOrder": {"owners": ["AG0", "AG1", "AG2", "AG3"], "required": ["operation_id", "requester", "assignee", "decision_needed", "decision_type", "scope", "output_contract", "goal_and_criteria_refs", "material_refs", "event_refs", "current_restrictions", "basis_revisions", "execution_epoch", "authority_scope", "authorization_refs", "shared_budget_ref", "stop_condition", "return_owner", "next_trigger", "acceptance"]},
    "WorkResult": {"owners": ["AG0", "AG1", "AG2", "AG3"], "required": ["work_order_ref", "handled_scope", "unhandled_scope", "result_refs", "limitations", "adoption_needed", "next_owner", "next_trigger", "compatibility", "adoption"]},
    "AuthorizationGrant": {"owners": ["USER", "AG1", "AG2", "AG3"], "required": ["issuer", "grantee", "decision_types", "object_scope", "criterion_refs", "permitted_conclusions", "escalation_signals", "budget_ref", "delegable", "validity", "binding_status"]},
    "BudgetEnvelope": {"owners": ["AG1"], "required": ["user_active_time", "blocked_wait", "system_effort", "fees", "allocation_scope", "authorization_ref", "accounting_notes"]},
    "ControlState": {"owners": ["AG0"], "required": ["state_revision", "restrictions", "execution", "record_policy", "pending_controls"]},
    "UseRestriction": {"owners": ["USER", "AG0", "AG1", "AG2", "AG3"], "required": ["scope_refs", "intended_uses", "reason", "issued_by", "status", "restoration_conditions", "restoration_refs"]},
    "CorrectionCase": {"owners": ["AG0", "AG1", "AG2", "AG3"], "required": ["changed_refs", "reason", "affected_refs", "unknown_dependencies", "restriction_refs", "material_recovery", "judgment_recovery", "teaching_recovery", "planning_recovery", "next_owner", "next_trigger"]},
    "SessionCheckpoint": {"owners": ["AG0"], "required": ["activity_ref", "parent_artifact", "last_trusted_event_ref", "help_history_refs", "next_connection", "stop_reason", "pending_owners", "budget_ref", "control_ref", "unrecorded_actions"]},
    "ChangeNotice": {"owners": ["AG0", "AG1", "AG2", "AG3"], "required": ["changed_refs", "reason", "immediate_restriction_refs", "direct_dependencies", "unchecked_scope", "restoration_conditions", "return_owner"]},
    "DependencyEdge": {"owners": ["AG0", "AG1", "AG2", "AG3"], "required": ["from_ref", "to_ref", "relation", "scope", "provenance"]},
    "ValidationDecision": {"owners": ["DEVELOPER", "AG1", "AG3"], "required": ["validation_layer", "case_id", "host", "versions", "executor", "checker", "raw_output_ref", "status", "limitations", "cost", "decision", "replay_of"]}
  }
}
```
