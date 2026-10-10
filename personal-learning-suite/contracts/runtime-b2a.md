# B2a 目标候选适配接口

日期：2026-10-03。共用对象语义仍为 `pl-contracts/0.1.0`；目标精简资源为 `pl-goals/0.1.0`，辅助程序输入为 `pl-goals-input/0.1.0`。公共必备字段及权限只由[共享契约](shared-contracts.md)维护，B1 保存仍按[原承载接口](runtime-b1.md)。

## 责任和能力

`learning-goals` 由模型依据当前用途、合法来源与目标规则完成设计、澄清或修订。`learning_goals.py` 只检查已经编写的结构化虚构候选、发现版本差异并包装交付；它不从正文自动抽取目标，不核内容真伪，不作评分、掌握或正式采用，不写数据库。脚本输出到 stdout；调用者自行保存的输出属于外部副本，不纳入 B1 数据库删除能力。

开发 CLI 仅接收 `synthetic_only=true` 与 `FIX-*` 对象。真实课程分析可以使用 Skill 指导，实际记录仍待宿主及实例授权绑定；开发态角色名不能当身份认证。来源核验记录是输入声明，完整性检查不升级其核查程度，也不生成 AG2 或 AG3 的独立回执。

## 输入与嵌套表示

顶层字段为 `input_version/synthetic_only/mode/goal/sources/course_map/unresolved_items`；修订或复用另给 `previous_goal` 与 `change`。`mode` 为 `design/revise/reuse`。`goal=null` 表示只有地图和缺项，不能用空判据冒充完整近期目标。

`goal` 使用 `GoalSpec` 公共字段；本切片细化近期嵌套表示：

| 位置 | 当前适配约定 |
|---|---|
| 目标 | `scope/excluded_scope` 用列表表达对象域与不覆盖范围；本适配把 `allowed_resources/context_conditions/time_requirements` 表为 Fact；已知资源与情境值用非空说明文字或列表，无额外工具明确写出，不改 B0 其它合法载体 |
| requirement | 稳定 `requirement_id`；`object_scope/key_operations/product/criterion/criterion_revision/nature` 及双来源 |
| nature | `course_explicit/user_purpose/system_suggestion/pending_clarification`，身份不从来源文件名推断 |
| criterion | `text` 表达关键正确性标准，并有 `requirement_source_refs/content_basis_refs` |
| prerequisite | `dependency_kind=necessary/companion/background`；`capability/task_resource_reason/tool_substitution/sufficiency_and_return`、要求定位 `requirement_ids`、双来源与 `learner_state` Fact；`necessity_basis` 说明依据，单次失败不能确立必要性 |
| evidence_requirements | 逐要求列表：`requirement_id/support_claim/required_operations/observable_product/allowed_help/task_coverage/cannot_infer`；操作按同一标识引用全部关键操作，已知帮助值用非空说明文字或列表 |
| sources | 完整 `SourceFragment`；双来源精确引用对象修订。统一表示为 `read_scope.text/formula/figure` 三 Fact、`verification.content`、主张列表与 `unread_parts` Fact；正文身份和定位保留在 `source_ref`；原单 Fact 虚构表示兼容读取 |

2026-10-04 起接受[共享契约](shared-contracts.md)的统一来源表示。`verification.content` 的 supported 声明须引用本来源修订，保留 AG2、合法方法、非空 scope／conditions、明确 unchecked_scope 和可定位锚点。`required_modalities` 是 AG2 明确给出的当前核验范围，不能从读清的模态数或目标文字猜测；其中每个模态的 Fact 须为 known 且有实际内容。缺该范围、必要模态未知、核验待查或版本失配时只限制关联要求，已有可靠子范围保留。其他非必需模态可保持 unknown。声明形状和定位均不能代替专业核验，原件锚点实际可用性还由受控保存及材料入口核对。

旧格式 `verification={status:known,value:{recorded_status:supported_for_fixture,method,scope,limitations}}` 与单 Fact `read_scope` 保留既有虚构目标检查行为，原夹具和历史报告不改写。这是读取兼容，不是运行迁移：程序不把粗读清描述自动填成三模态 known，也不把 `supported_for_fixture` 改成通用内容正确性状态。进入材料阶段前需 AG2 显式提供统一模态与核验记录；仍缺模态则合理停止。B5 的 `goal.sources_submit` 保存原包的精确来源，`goal.submit` 使用相同引用；统一来源可再用于材料检查／提交，无需改写其读清与未知事实。对真实资料不得使用虚构核验标记。

`course_map` 为 `topics:[{topic,final_task,status}]`、`deferred_goals:[{topic,provisional_scope,refine_when}]` 和 `refine_triggers`。它是目标包的本地说明视图，未另建数据库或共享对象；没有学习者掌握字段。

`unresolved_items` 项含 `decision_needed/owner/next_trigger/scope_requirement_ids`。指明会改变哪个决定，谁接手及何时补齐；远期缺项与当前关键缺项分开。

作用域 ID 必须属于当前要求；空列表表示明确的远期／非当前要求缺项。顶层双来源是逐要求／判据／前置来源的聚合，已定位的来源缺项只限制其关联要求；没有局部定位的顶层依据按共用依赖处理。缺来源记录及未知依赖保持保守限制，不能从未知推断无影响。

`change={kind,reason,requirement_mapping,equivalence_reason?}`，映射项为 `{from_requirement_ids,to_requirement_ids,relation}`。`kind` 支持 `session_budget_only/equivalent/split/merge/substantive/correction/purpose_change`。语义详见[版本规则](../src/skills/learning-goals/references/version-rules.md)。结构相似不能代替等价论证。

## 输出、版本与保存

公开函数 `review_goal_package(package)` 返回 JSON 可序列化的候选报告；CLI 使用：

```powershell
python -X utf8 personal-learning-suite/src/runtime/learning_goals.py --input personal-learning-suite/fixtures/b2a-goal-input.json
```

结果保持 `candidate`；`review_state` 区分 `complete/partial/map_only/invalid`。`goal_candidate`、按输入记录获得支持的 `reliable_requirement_ids`、未决项、错误和限制使已处理范围可核查；“reliable”仅指结构与所给核验记录支持，不能解释为程序已核验学科内容。`complete` 也不代表正式采用、参考可评分或目标达成。

报告版本是 `pl-goals-review/0.1.0`。`work_result_view` 明示为不可直接持久化的本地预览，给已处理／未处理范围、结果引用、采用需要和下一责任；未提供正式工作单时 `work_order_ref` 用不适用说明，不冒造 `WorkOrder`。stdout 不复制来源全文，交接时须同时提供原输入来源包或共享组件的合法精确引用；单独一份 stdout 不能代替完整 P-Goal 的来源条件。

`compatibility` 列出保留范围、重核范围和理由。兼容检查保持旧目标与旧证据原范围，不复制／扩展 `Judgment`；实质判据变化须增判据修订。拆并映射只是复核输入，新增综合工作仍待证。纯会话缩时复用相同目标并返回 `planning_handoff`，不生成 `PlanCommitment`。

真正修订时，程序把比较结果以 Fact 写入 `goal_candidate.version_compatibility`，避免候选仍标“首版无历史”；复用和会话缩时保持整个原目标不变。等价保留须有逐项同身份映射和理由，跨能力互换映射不作等价保留。

纠错返回 `change_notice_candidate` 及 `restriction_execution=not_executed`。这是 P-Change 候选本地视图，尚未作为正式 `ChangeNotice` 提交；控制入口须先落实用途限制。AG2 更正内容、AG1 修目标、AG3 重评原答、计划及实际教学恢复分别处理，原答是否充分由 AG3 判断。

本批在隔离临时空间验证有效候选可经 B1 的现有授权、采用依据和 CAS 提交后精确读回；没有自动采用命令。采用者先核当前控制、合法来源与真正授权，再通过 `LearningStore.commit`；脚本预览成功不提供写入权限。来源限制、暂停、删除后的迟到结果及旧修订提交仍由共享组件拒绝，候选不解除限制。

## 验收范围

程序行为测试和独立 Skill 前向试用分开报告。虚构输入验证可观察的目标结构、未决子范围、版本及 B1 接口，不证明真实课程有效性、正式参考核验、V3 学习成效或 V4 四角色／七 Skill 的增益。B2b、B3a、B4 教学与计划及 B6 宿主网络能力另行实现。
