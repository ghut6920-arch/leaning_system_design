# B4 计划接口

共享协议 `pl-contracts/0.1.0`；局部协议 `pl-planning/0.1.0`。入口 `PlanningService(LearningStore(..., entry_actor="AG1"|"AG0"))`，只处理隔离人工记录。计划优先与学习内容由模型／责任方决定，程序检查声明、控制和预算，不生成日历或实际效果结论。

`inspect(request)` 只返回 candidate 与声明费用；`run(request)` 显式受控保存；`resume(commitment_ref)` 只读当前有效安排与合法断点。CLI `--workspace --request --actor AG1|AG0 [--inspect]`，stdout JSON。不存在／损坏请求也返回 JSON rejected。

通用请求：`synthetic_only=true`、action、budget_ref、decisions。正式 run 加 expected_state_revision、operation_id、authorization_refs；decision 引用现有 need_ref，有 reason/uncovered_impact/next_trigger。同需求一次一个决定；检查最新目标、引用与用途。正式计划授权为 planning，AG0 shrink 为 plan_adjustment，专业提交沿原 Store 采用门。专业采用引用与会计声明保存在现有对象 metadata.planning，不另开数据库。

| action | 真实效果 |
|---|---|
| accept | AG1 接责该需求，disposition 保持 pending，没有新承诺 |
| dispose | deferred/no_further_investment/closed/merged/returned，返回真实理由、影响和触发 |
| schedule | AG1 安排 scheduled/partially_scheduled，可同时处置其他需求；创建一个有效计划 |
| shrink | 授权 AG0/AG1 缩既有 commitment_ref；保留原设计、判据、条件，不扩大投入 |

安排 decision 增加：activity_ref、requirement_ids、operations、scope、cost、material_context（B3 材料上下文）、readiness（necessary_conditions/feasible_stop/scope_confirmed 三个 known true Fact）；配置存在时提供 strategy_context。计划要求当前活动、采用材料与合法执行准备；专项再核 GoalSpec 教学范围和整体参考。

cost 结构：user_active 内 preparation_verification/context_recovery/learning/feedback_check/closure_switch/maintenance_correction，每项为 known value `{minutes,basis: observed|bounded_trial|estimate,source}` 或 not_required reason。closure_switch 必须留正时长。blocked_wait/system_effort 为 known value minutes 或 not_required；fees 为 known value amount 或 not_required。unknown 不变零。estimate 必须有 reserve_minutes>0、uncertainty_reason。数值仅是调用方声明，会计比较容忍十亿分之一分钟浮点误差，不认证测量。

schedule 还给 plan_id、spent_minutes（known value minutes）、reserve_minutes、allowed_adjustments、可选 checkpoint_ref/next_trigger。所有安排与已耗用／余量共用预算；保存的 C0 同预算累计时长形成 spent 下界。当前有限实现同 BudgetEnvelope 只一个有效 PlanCommitment，多个目标放其 allocations，不给每项完整额度。

耗用下界同时检查同预算、同活动、确切事件身份相容且合法可读的 SessionCheckpoint 累计声明，取最大值而不重复相加。修复前检查点较事件记录更高的时长也不能被旧 spent 声明覆盖；仅取其预算事实，不采用旧安排或历史教学决定。无关检查点不进入预算依据；匹配耗用的检查点受控不可用时返回 blocked，不披露其受限事实，也不将其跳过后视为零支出，原专业与控制门仍先行。

shrink 提供 commitment_ref、available_minutes、全部原 need 的 decisions，以及比较 alternatives。allowed_adjustments 是 `{actions:["shrink"],need_ids:[...],preserve_conditions:"..."}`。每个操作／覆盖为原子集，材料上下文与活动不可变，成本与额度不能增；否则交 AG1 候选。全部暂缓时 plan stopped。缩范围与缩成本须有真实可行性声明，程序不证明微缩教学等效。

合并 decision 给 merge_target_ref 与 requirement_mapping，要求同目标、条件和父任务，目标仍有效。当前有限实现只准同一要求 ID 的恒等映射，目标需求完整包含源要求；不能把整体要求换成局部要求。不同 ID 的专业等价关系不在此自动合并范围。关闭 decision 给 evidence_refs（已采用 Judgment、supported/usable、planning_closure 用途）与原 material_context；AG0 routine_scoring 或 AG3 的专业授权与时间等由 B3a 复验。证据不足不关闭；关需求不证明目标永久掌握。

替换有效安排须给 replace_commitment_refs，实质处理其全部需求；多个需求／替换须 alternatives（每项 scope/consequence）。旧计划同事务 superseded，旧需求不留“安排在已无效计划”。CAS/幂等及引用控制沿原存储；控制在重放前，失败 output_refs 为空。标准库没有实际计时、提醒、自动排程、主入口路由或真实宿主绑定，分别留后续实施。
