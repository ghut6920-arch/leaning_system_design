# B4 教学专项接口

共享对象保持 `pl-contracts/0.1.0`，C0 保持 `pl-teaching/0.1.0`；专项协议为 `pl-teaching-b4/0.1.0`。入口是 `runtime.learning_teaching_b4.SpecializedTeachingService.run(request)`。仅支持人工虚构、单入口顺序工作区。

## 设计与采用

`design`：AG1 提供 `activity`（完整 ActivitySpec）和 `context`（与 B3b 相同的材料用途上下文）。返回候选与执行条件，不保存。`commit_design` 使用同样输入，加 `expected_state_revision/operation_id/authorization_refs/adoption_refs`；活动必须声明 AG1 adoption，决定类型 `teaching_design`。同一 Store 检查正式授权、采用、CAS、当前依赖；候选成功不表示可以执行，执行仍由 C0 核当前材料用途和授权。

ActivitySpec 在 `metadata.b4` 保存：

```json
{
  "version": "pl-teaching-b4/0.1.0",
  "module": "post",
  "work": "连接给定前提并返回同一整体论证",
  "needed_structure": "前提与结论之间的合法关系",
  "change_and_hold": {"change": ["连接的表达"], "hold": ["给定前提"], "allowed_additions": []},
  "acceptable_products": ["有合法理由的不同等价表达"],
  "post_function": "integration",
  "whole_required": false,
  "whole_reference_refs": [],
  "whole_obligations": [],
  "interfaces": [],
  "branch_routes": ["enter_encoding"]
}
```

`post_function` 为 `recovery/integration/selection/update`；Encoding 可以省略。每一 C0 branch 对应一个 route：`explain/goal_work/withdraw_help/conditions/whole/enter_encoding/enter_post/end/change_route/return_local/hold_for_review`。每个分支须具 observation/action/next_observation/counterevidence/stop。不统一排名、深度、卡数或活动顺序。

每个引用的 GoalSpec requirement 必须有 `teaching_scope={whole_required: bool, whole_obligations: []}` 的当前专业声明；缺项交 AG1，不猜文字复杂性。整体要求继承自目标，活动不能取消；明确局部子任务可声明 `goal_coverage=local_only` 且操作须为整体要求的严格子集，整体未支持仍保留。旧目标不批量迁移。整体活动必须有整体核验引用和非空整体义务；引用 MaterialUse／SourceFragment 的 `verification.content.whole_coverage` 声明 supported，goal_refs/criterion_refs 覆盖本目标判据，target_operations/obligations 覆盖实际工作，anchor_refs 合法；checked_revision 为当前修订。缺项 `not_ready`，不把局部参考冒作整体依据。软件核声明／引用，不证明学科真伪。接口可选，每项须明确 input/output/conditions/reliable_properties/internal_unknown；未知内部不伪造。

## 执行与双向返回

C0 的 open、record_initial、record_help、record_revision、record_feedback、checkpoint、close、return_parent、resume 原请求完整兼容。B4 只用于带专项 metadata 的活动，使用 C0 原检查与同一次事务。初答保存时在 PerformanceEvent.metadata.b4 保存 module、空 stack 与 transition_history；同题修订保留独立样本 ID。辅助器不评分、不产生目标掌握度。

`select_branch` 只读：提供 `event_ref/branch_index/observation`；observation 是 `{artifact_ref, quote}`，必须位于本事件的已存原答／修订。返回该已准备分支、当前条件与下一动作候选，不自动执行或诊断。读到参考／配置不表示展示。

`enter_local` 写入：提供当前 `event_ref`、CAS 与 AG0 执行授权、`local`：

- `module` 与当前模块不同，`operations` 是当前活动操作的非空子集；
- `reason/blocker/local_sufficiency/return_connection` 为具体非空说明；
- `alternative_explanations` 非空，`preserved_support_refs` 为确切记录引用（可空）；
- `observation` 为本事件原答／修订锚点与原文 quote；
- `premises_supplied` 为布尔 Fact。Post→Encoding 必须 known true，且当前时间线已有实际 displayed 帮助、其后有对应修订原答；把“取不出”直接诊断成结构问题会被拒绝。

保存同一父 activity、进入前响应产物、返回连接、同一预算、scope、帮助边界，向本事件 timeline 添加 backend_reference 控制项；不重置接触，不复制父产物，不产生新事件。

嵌套进入必须引用当前局部进入后新保存的学习者响应；同一操作范围在返回后重进，还须引用上次该范围返回后新的父任务响应。`transition_history` 保留这一约束，弹出局部栈、重开工作区或换一段 reason 不重置观察条件。没有新响应返回 `not_ready/new_local_observation_required` 与换路／收束候选，状态不变；真实新响应可继续局部工作，不设固定深度或轮数。任务、前提或使用条件确有变更时，走正常 ActivitySpec 设计／采用和材料用途核验，不能以新增 reason／blocker 声明代替新依据；本有限接口不自动判定新作答是否具有学科上的新增信息。

`return_local` 写入：提供 `event_ref`、`return_connection`（与栈顶相同）、`local_observation`（进入后的已存修订锚点与 quote）、`local_outcome`（`sufficient/no_progress/contradicted`）、`parent_outcome`（`not_observed/still_blocked`）。只恢复原模块和返回点，保留局部结果／原帮助；父整体和目标条件不自动通过。返回仍阻塞时给出 review_interfaces_or_close 候选，不自动继续下钻。同模块追加工作使用 C0 修订，跨 ActivitySpec 父任务返回使用原 C0 return_parent。

`review_whole` 只读：提供 `event_ref/product_ref`（本事件连续原答／修订产物）、`requirement_ids`（活动要求）、`intended_use`。整体要求使用已有整体核验引用；返回完整原件、目标义务、真实帮助和 SK04 的重要复核 handoff，`overall_support=not_assessed`。局部成功数不替代完整论证；合法不同解交 AG2/AG3 审核，不机械匹配参考。

`reuse_evidence` 只读短路径：提供 `goal_ref/requirement_ids/judgment_refs/intended_use`。只读当前、已采用、supported/usable、无反证、用途覆盖的判断及受控原件依赖，引用原条件返回 `sufficient_for_declared_use`；不能外推到未授权用途、未满足时间或独立条件。未覆盖要求返回 `needs_work`。此检查不新评判，也不追加题；计划方可据此处置同一需求。

## 恢复与边界

checkpoint 指向包含专项状态的同一最新事件；B4 resume 返回模块、局部栈和 transition_history。写入只用原 LearningStore 的一个事务。控制、删除和引用检查在幂等重放前；失败不返回已保存交接或下一动作。仅缺未来目标时间时用 C0 close 结束并交目标内 LearningNeed 候选；近期反馈时序和持久支持由 B3a 检查，B4 不按日历推断。

B4 不实现 B5 自动调用／需求接责，不绑定 B6 真实角色或显示宿主。直接调用旧 B3b 入口不会执行 B4 metadata 检查；专项活动使用本入口，B5 再落实统一路由。程序检查声明和范围，内容、局部够用和完整产物的专业结论仍须 AG2/AG3 有依据判断。
