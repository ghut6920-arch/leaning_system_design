# B6 受控本地工作网络接口

日期：2026-10-03；局部适配 `pl-network/0.1.0`，共用字段仍以 [共享契约](shared-contracts.md) 唯一维护。专业动作继续使用 [B5 接口](entry-b5.md) 和相应 B2—B4 契约。

## 宿主建立与可信边界

`NetworkHost(store_or_root)` 只打开已初始化的虚构工作区；可以用 `PersonalLearningEntry(store).open_network()` 创建。用上下文管理器或 `close()` 释放操作系统锁。每个工作区同时只允许一个合作宿主；Windows 使用 `msvcrt`，其他平台使用 `fcntl`，不创建个人内容的锁缓存。

可信本地调用方使用 `bind('AG0'..'AG3')` 得到只属于本宿主实例的能力对象；它不能用字符串或 JSON 替代，也不能跨宿主或关闭后继续使用。`role_info(capability)` 返回实际加载的角色、Skill 路径和指导。该通道不提供外部服务登录、自然人认证、模型 API 或任意工具执行；实际模型名称保持未绑定。

每个结构化请求要求 `network_version='pl-network/0.1.0'`、`synthetic_only=true`。变更还需 `expected_state_revision` 与非空 `operation_id`。请求不能自报 `actor/entry_actor/executor_id/capability`。主宿主持有绑定能力；专业模型／调用者只得到已授权能力和最小上下文。

## 工作单与返回

| 方法 | 请求及含义 |
|---|---|
| `dispatch(cap, request)` | `order_id/assignee/decision_needed/decision_type/scope/operation/professional_request/context_refs/authorization_refs/shared_budget_ref/stop_condition/next_trigger/return_owner`；可附 `goal_and_criteria_refs/material_refs/event_refs/operation_scope` |
| `accept(cap, request)` | `order_ref/status/handled_scope/unhandled_scope/limitations/next_trigger`；`received` 只读，`accepted/partially_accepted/declined` 明确接责或拒收 |
| `context(cap, order_ref)` | 读取工作单允许的对象和合法原件定位；事件原始依据排在前，限定原件段需显式定位 |
| `run(cap, request)` | `order_ref/result_id`；执行工作单保存的一个固定专业动作，调用方不能改动作或专业载荷扩大范围；返回引用式候选 WorkResult |
| `adopt(cap, request)` | `result_ref/status/basis_refs/limitations`，可附处理／未处理范围和触发；`adopted/partially_adopted/recheck/rejected` 由对应专业责任明确决定 |
| `pending(cap)` | 只读待接责／待处理／待采用／受限结果、未覆盖范围、责任及触发；同一工作单可按不同未决结果返回多条，不返回完整专业正文 |

`scope/operation_scope` 在本有限适配中使用专业操作的目标对象 ID；人类工作描述写在 `decision_needed`。专业载荷不得引用未声明依据，不得另给总预算。`professional_request` 使用已有专业契约，并带 `synthetic_only=true`，不提供自己的状态修订；正式专业步骤用运行时实际修订，写步骤的原 `operation_id` 保持一个逻辑变更。

缺接收者授权时，WorkOrder 使用明确 `metadata.network.version/phase=proposed_unready` 与 `acceptance.status=proposed`，仍可持久保存待处理责任；此候选例外不允许接责或运行。有授权时还要检查主体、有效性、对象、判据和同一预算。模式与角色规则不扩权。

WorkOrder 的 requester 保留发送责任，接责修订记录受托人实际承担的范围；部分未接范围仍由发送者跟进。仅收到不推进修订。WorkResult 的元数据仅记专业状态与返回阶段，完整专业事实仍来自原对象，不缓存完整工具响应。返回失败不能宣称全部已处理；专业保存已成功而网络回执失败时报告实际保存前缀和未完成范围，不把它回滚成未发生。

2026-10-04 未决可见性修复：同一已接责工作单仍允许不同逻辑 `operation_id/result_id` 显式执行同一个原专业请求；同一逻辑操作的幂等重放不新增结果。各结果分别保存采用状态，新结果不按 ID、返回先后或另一结果的采用自动取代旧结果。`pending` 对每个结果复查其本身、依据及专业产物的当前控制与版本；当前合法且 `adopted` 的结果单独结束待采用责任，不能隐藏另一个候选。`partially_adopted/recheck/rejected` 继续按原未处理范围和触发保留跟进，拒绝某次返回不等于已处置整个工作单。没有结果时仍返回原工作单的待接责／待处理项；受限或过期结果只返回工作单层级的 `blocked=true/adoption=recheck/result_ref=null`，不返回该结果引用或正文。

采用检查控制、当前引用、授权、处理范围与限制。候选 WorkResult 的 adopted 仅表示网络专业返回被接纳；不会暗中采用其候选 GoalSpec、改 Judgment 或排学习。原专业保存仍需其专门授权和采用门。过期依据保守重核；不同修订的事实复用需相应专业明确重核，不将旧总结当新证据。

## 执行、展示和控制

`takeover(cap, request)` 仅 AG0：`activity_ref/basis_refs/expected_epoch` 加变更字段。宿主补足当前活动的目标／判据、材料／参考、教学授权和共享预算引用，并校验完整已记录上游依赖的当前版本。接任者通过已有 `execute` 的教学 `resume` 路径核对父产物、实际帮助及可信事件，未知动作保持未知；执行权回执本身不证明已经读完原答。已有 active 执行时要求准确旧 epoch。

LearningStore 的专用 `set_execution` 原子保存规范 ControlState、增加执行代次并提交回执；普通 commit 仍不能写 ControlState。`check_execution` 每次重读控制、准确活动、执行者和代次；旧执行回执不能恢复被接管的入口。删除关联索引可移除代次历史，因此通道另靠删除后的能力终止及不可复用随机执行者身份拒绝旧票据，不保留被删个人关联作为暗中高水位。

`present(cap, request)` 仅当前 AG0：`activity_ref/execution_epoch/basis_refs/professional_request`；后者是原教学 `action=open` 请求，准确对应活动。展示前后都经过当前执行门，返回只包含原 learner_packet 的 `prompt/visible_input`。教师参考、备用帮助和全工具回执不会随该返回外显。

`execute(cap, request)` 是 AG0 的已有可靠活动／常规授权短路径：`operation/professional_request` 加变更字段，只允许 `owner_for` 属于 AG0 的动作。教学仍需当前执行门，不要求先创建四方工作单；只返回安全专业引用／有限恢复视图。`open` 的题面只通过 `present` 返回。

`control(cap, request)` 仅 AG0：`action=pause/restrict/resume/delete`、`scope_ids` 及变更字段；暂停／限制附理由，限制附用途，删除可明确 `include_indexes`。沿既有两阶段删除，不会解除专业限制。删除终止受影响本地能力，后续重新绑定并以剩余合法依据建立工作；不把此前拿到的上下文当当前依据。

所有宿主调用按 RLock 串行。当前没有异步发任务、后台 worker、定时续跑或并行展示 API；旧开发脚本、直接共享文件写入、Codex 聊天及外部模型上下文均不在该管道保障内。stdout、调用者已保存的响应及外部历史不扩大删除承诺。七个 Skill 仍未安装为自包含发布包；真实实例及效果检验继续留 B7。
