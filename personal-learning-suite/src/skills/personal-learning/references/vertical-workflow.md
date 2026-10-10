# B5 单入口纵向工作流

在需要落实专业动作时读取本文件；仅查看、恢复定位、候选路由和控制操作仍读 [entry-controls.md](entry-controls.md)。完整 envelope、动作表、绑定和回执见 [B5 接口](../../../../contracts/entry-b5.md)。

## 选择够用路径

先核当前控制、目的、已有可用对象和预算。执行请求必须是明确动作及其专业载荷；自然语言意图只给候选 route。已有可靠活动直接 `teaching.run`，已有原答直接评估；已有合格证据直接交计划处置，不强制重新设计、核验、选卡或加题。

| 当前工作 | 选择的动作／责任 |
|---|---|
| 目标缺失或正式变更 | `goal.review` 后先由 AG2 `goal.sources_submit` 保存原 package 来源，再由调用方提供 AG1 明确采用的 `goal.submit` |
| 材料读取／用途有缺项 | `materials.read/inspect/submit`；AG2；读取不等正确性或用途核验 |
| 关键活动设计 | `teaching.run` 的 `design/commit_design`；AG1；实际执行条件另核 |
| 当前已授权教学 | `teaching.run` 的 C0／Encoding／Post 动作；AG0；保留同一父任务和帮助 |
| 常规原答判断 | `assessment.routine_inspect/routine_submit`；AG0；须有效常规评分授权 |
| 重要判断、异议或诊断 | `assessment.inspect/diagnose/submit`；AG3；入口不替代独立复核 |
| 同一后续需求 | `need.submit` 仅新 ID 提出／待处理；已有需求更新及实质去向用 `planning.inspect/run`；AG1 |
| 授权缩时／恢复 | `planning.run` 的 `shrink` 由 AG0；`planning.resume` 只读合法承诺 |
| 需要重新选法或维护配置 | `strategies.inspect/reuse/submit`；AG1；稳定有效配置直接复用 |

## 准备、调用与返回

`PersonalLearningEntry.execute(request)` 或主入口 `execute --request` 接收 `entry_version=pl-entry/0.1.0`、`synthetic_only=true`、当前 `expected_state_revision` 和顺序 `steps`。专业内容、评分理由、实际过程、授权及采用由调用方显式提供，入口只连接既有服务。每个写步骤保持自己的 `operation_id`，不在步骤中提供 CAS 或 actor。

把前步已返回的精确引用绑定到后步 request 内已有占位，源路径相对前步 `result`；不能绑定控制字段、自身或未来结果。正式后续仍复验 Store 中对象，候选不能作为已保存依据。目标来源通过 AG2 专门动作保留原 B2a Fact 与核验声明，不猜造 B2b 模态字段；已有相同引用的来源／目标内容须与保存对象一致。目标提交允许调用方显式改变 adoption、authorization_ref、decision_type，其余内容必须与检查候选一致；入口不自动采用，显式决定类型必须属于相应对象的专业责任。

按步查看原服务 `status/result` 与入口 `stage`。`completed` 仅为全部请求调用返回；`candidate/checked/limited` 不称已保存，`saved` 不称目标达成或需求已安排。展示使用 `user_view` 的当前工作、活动事实、条件化支持和本次关联需求去向及控制；按 goal_ref 区分范围，技术 result 中的教师参考、提取文本或原件不直接展示。

链中失败立即停止后续，已保存前缀如实保留；整链不回滚、不自动重放。重读当前控制和修订，复核剩余范围后再调用。未决返回 owner、decision_needed 与 next_trigger；没有实际接责和计划提交时维持未处理，不能说“已安排”。保存失败保持待保存，候选和 stdout 不是跨会话恢复来源。

## 收束与恢复

原答、真实帮助和修订按发生顺序保存，同题修订不新增独立样本；局部 Encoding 够用后回同一父产物，不重置暴露或需求。收束沿同一 LearningNeed；已有需求不能再用 need.submit 重写。close 候选的未决只在同链计划保存该需求的实质非 pending 去向后解除，接收或 acceptance 本身仍未决。未来必要时间条件未满足时保持未完成，不靠即时加题填补。

原 `resume` 和 `planning.resume` 只定位可信断点及合法依据；缺摘要不重测整章，不推断未记录动作或无帮助。用户暂停与专业用途限制分别处理，解除暂停不解除专业限制。删除后只用剩余合法依据，不能从迟到结果或候选补回原件。

当前只有虚构单入口串行兼任，没有真实 Agent 身份、后台工作单接责、自动提醒、独立会签或旧输出隔离。需要这些宿主能力时保持受限并交 B6 实现；不能把专业 owner 字符串当作真实授权。
